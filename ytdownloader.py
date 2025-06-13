import os
import subprocess
import time
import streamlit as st
import json
import re
from functools import lru_cache

def is_youtube_url(text):
    # Regular expression to match YouTube URLs
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.match(youtube_regex, text)
    return bool(match)

def extract_video_id(url):
    # Extract video ID from YouTube URL
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.match(youtube_regex, url)
    if match:
        return match.group(4)
    return None

# Cache the search results for 5 minutes
@st.cache_data(ttl=300)
def get_search_results(song_name, num_results, offset=0):
    try:
        # Calculate total results needed
        total_results = offset + num_results
        command = [
            "yt-dlp",
            f"ytsearch{total_results}:{song_name}",
            "--skip-download",
            "--dump-json",
            "--no-warnings",  # Reduce output noise
            "--quiet"  # Make it quieter
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            # Split the output by newlines and parse each JSON object
            results = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    results.append({
                        'title': data.get('title'),
                        'thumbnail': data.get('thumbnail'),
                        'duration': data.get('duration'),
                        'id': data.get('id')
                    })
            # Return only the new results (from offset to end)
            return results[offset:]
        return None
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return None

def download_media(video_id, format_type, quality, output_path="downloads"):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        # Generate a unique filename template
        timestamp = int(time.time())
        ext = 'm4a' if format_type == 'MP3' else 'mp4'
        output_template = os.path.join(output_path, f"%(title)s_{timestamp}.%(ext)s")
        
        # Create a placeholder for progress
        progress_placeholder = st.empty()
        progress_bar = progress_placeholder.progress(0)
        
        with st.spinner(f"Preparing {format_type} download in {quality} quality..."):
            # First get video info
            info_command = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "--dump-json",
                "--no-playlist",
                "--no-warnings",
                "--quiet"
            ]
            info_result = subprocess.run(info_command, capture_output=True, text=True)
            if info_result.returncode != 0:
                st.error(f"Failed to get video info: {info_result.stderr}")
                return None
            try:
                video_info = json.loads(info_result.stdout)
                title = video_info.get('title', 'video')
                # Clean the title to make it safe for filenames
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                prefix = os.path.join(output_path, f"{title}_{timestamp}")
                
                # Now download the file with progress and print the actual output path
                command = [
                    "yt-dlp",
                    f"https://www.youtube.com/watch?v={video_id}",
                    "--output", output_template,
                    "--no-playlist",
                    "--no-warnings",
                    "--newline",
                    "--progress",
                    "--no-overwrites",
                    "--no-continue",
                    "--merge-output-format", "mp4",
                    "--print", "after_move:filepath"
                ]
                # Add format-specific options
                if format_type == "MP3":
                    if quality == "320k":
                        command.extend(["--format", "bestaudio[ext=m4a]/bestaudio/best"])
                    else:
                        command.extend(["--format", "worstaudio[ext=m4a]/worstaudio/worst"])
                else:  # MP4
                    if quality == "Best":
                        command.extend(["--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
                    else:
                        command.extend(["--format", f"bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality[:-1]}][ext=mp4]/best"])
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
                output_file = None
                progress_pattern = r'(\d+\.\d+)%'
                for line in process.stdout:
                    if '%' in line:
                        match = re.search(progress_pattern, line)
                        if match:
                            progress = float(match.group(1))
                            progress_bar.progress(progress / 100)
                            progress_placeholder.text(f"Downloading: {progress:.1f}%")
                    elif line.strip() and os.path.sep in line:
                        # This should be the printed file path
                        output_file = line.strip()
                process.wait()
                # Robust file finding logic
                found_file = None
                if output_file and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    found_file = output_file
                else:
                    # Try to find any .mp4 file that contains the unique _{timestamp} before .mp4
                    files = os.listdir(output_path)
                    mp4_pattern = re.compile(rf'_{timestamp}(?:\..+)?\.mp4$')
                    mp4_candidates = [f for f in files if mp4_pattern.search(f)]
                    if mp4_candidates:
                        # Pick the largest file
                        mp4_candidates = sorted(mp4_candidates, key=lambda f: os.path.getsize(os.path.join(output_path, f)), reverse=True)
                        candidate_path = os.path.join(output_path, mp4_candidates[0])
                        if os.path.getsize(candidate_path) > 0:
                            found_file = candidate_path
                if found_file:
                    progress_placeholder.empty()
                    try:
                        st.toast("Your file is ready! Click the download button below to save it to your device.")
                    except AttributeError:
                        st.info("Your file is ready! Click the download button below to save it to your device.")
                    with open(found_file, 'rb') as file:
                        st.download_button(
                            label=f"💾 Save to Device ({format_type} {quality})",
                            data=file,
                            file_name=os.path.basename(found_file),
                            mime=f"audio/{format_type.lower()}" if format_type == "MP3" else "video/mp4",
                            type="primary"
                        )
                    return True
                else:
                    error_msg = process.stderr.read()
                    if not error_msg:
                        error_msg = "No error message available"
                    st.error(f"Download completed but file not found or empty. Error: {error_msg}")
                    # List files in the directory to help debug
                    if os.path.exists(output_path):
                        files = os.listdir(output_path)
                        st.error(f"Files in download directory: {files}")
                    if output_file:
                        st.error(f"Expected output file: {output_file}")
                    # Check for .part files
                    part_candidates = [f for f in files if f.startswith(os.path.basename(prefix)) and f.endswith('.part')]
                    if part_candidates:
                        st.warning(f"Found incomplete download: {part_candidates[0]}. The download may not have finished correctly.")
                    return None
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse video info: {str(e)}")
                return None
    except Exception as e:
        st.error(f"Error downloading {format_type}: {str(e)}")
        return None

def format_duration(seconds):
    if not seconds:
        return "Unknown duration"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def main():
    st.markdown("""
    # 🎵 YouTube Media Downloader
    
    **How it works:**
    - Enter a song name, artist, or video title in the search box, or paste a YouTube URL.
    - The app will search YouTube and show you the top results.
    - Choose your desired format (MP3/MP4) and quality.
    - Click 'Prepare Download' to fetch the file, then 'Save to Device' to download it.
    - You can repeat this for multiple songs or videos.
    
    **Features:**
    - 🔍 Search for music or videos by prompt (no need for YouTube URLs)
    - 🎧 Download audio (MP3) or video (MP4) in your chosen quality
    - 📥 Batch process: get multiple files by entering prompts one after another
    - ⚡ Fast, simple, and works on any device with a browser
    """)
    st.title("YouTube Media Downloader")
    
    # Initialize session state
    if 'mode' not in st.session_state:
        st.session_state['mode'] = 'search'
    if 'format' not in st.session_state:
        st.session_state['format'] = 'MP3'
    if 'quality' not in st.session_state:
        st.session_state['quality'] = '320k' if st.session_state['format'] == 'MP3' else '1080p'
    if 'search_results' not in st.session_state:
        st.session_state['search_results'] = []
    if 'current_offset' not in st.session_state:
        st.session_state['current_offset'] = 0

    # Format selection buttons
    st.write("### Select Format")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎵 MP3 (Audio)", type="primary" if st.session_state['format'] == 'MP3' else "secondary"):
            st.session_state['format'] = 'MP3'
            st.session_state['quality'] = '320k'  # Reset to default MP3 quality
            st.rerun()
    with col2:
        if st.button("🎥 MP4 (Video)", type="primary" if st.session_state['format'] == 'MP4' else "secondary"):
            st.session_state['format'] = 'MP4'
            st.session_state['quality'] = '1080p'  # Reset to default MP4 quality
            st.rerun()

    # Quality selection based on format
    st.write("### Select Quality")
    if st.session_state['format'] == 'MP3':
        quality = st.select_slider(
            "MP3 Bitrate",
            options=['96k', '128k', '192k', '256k', '320k'],
            value=st.session_state['quality'],
            help="Higher bitrate means better quality but larger file size"
        )
    else:  # MP4
        quality = st.select_slider(
            "Video Resolution",
            options=['360p', '480p', '720p', '1080p', 'Best'],
            value=st.session_state['quality'],
            help="Higher resolution means better quality but larger file size"
        )
    
    if quality != st.session_state['quality']:
        st.session_state['quality'] = quality
        st.rerun()

    # Mode selection buttons
    st.write("### Select Mode")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Search Mode", type="primary" if st.session_state['mode'] == 'search' else "secondary"):
            st.session_state['mode'] = 'search'
            st.rerun()
    with col2:
        if st.button("🔗 URL Mode", type="primary" if st.session_state['mode'] == 'url' else "secondary"):
            st.session_state['mode'] = 'url'
            st.rerun()

    # Show different UI based on mode
    if st.session_state['mode'] == 'search':
        st.write(f"Enter a song name to search and download as {st.session_state['format']} in {st.session_state['quality']} quality.")
        
        # Add number input for results count
        num_results = st.number_input(
            "Number of results to show",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
            help="Choose how many search results you want to see (1-10)"
        )
        
        song_name = st.text_input("Song Name")

        if st.button("Search", type="primary"):
            if song_name:
                with st.spinner("Searching..."):
                    results = get_search_results(song_name, num_results)
                    if results:
                        st.session_state['search_results'] = results
                        st.session_state['current_offset'] = num_results
                    else:
                        st.warning("No results found.")
            else:
                st.warning("Please enter a song name.")

        # Show search results
        if st.session_state['search_results']:
            st.write(f"### Search Results (Showing {len(st.session_state['search_results'])} results)")
            
            # Display all results in a single column
            for i, result in enumerate(st.session_state['search_results']):
                st.write("---")  # Add a separator between results
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(result['thumbnail'], use_container_width=True)
                with col2:
                    st.write(f"**{i+1}. {result['title']}**")
                    st.write(f"Duration: {format_duration(result['duration'])}")
                    if st.button(f"⬇️ Prepare Download ({st.session_state['format']} {st.session_state['quality']})", key=f"download_{i}"):
                        download_media(result['id'], st.session_state['format'], st.session_state['quality'])

            # Add "Load More" button
            if st.button("Load More Results"):
                if song_name:
                    with st.spinner("Loading more results..."):
                        new_results = get_search_results(song_name, 2, st.session_state['current_offset'])
                        if new_results:
                            st.session_state['search_results'].extend(new_results)
                            st.session_state['current_offset'] += 2
                            st.rerun()
                        else:
                            st.warning("No more results available.")

    else:  # URL mode
        st.write(f"Paste a YouTube URL to download as {st.session_state['format']} in {st.session_state['quality']} quality.")
        url = st.text_input("YouTube URL")
        
        if st.button("⬇️ Prepare Download", type="primary"):
            if url:
                if is_youtube_url(url):
                    video_id = extract_video_id(url)
                    if video_id:
                        download_media(video_id, st.session_state['format'], st.session_state['quality'])
                    else:
                        st.error("Invalid YouTube URL")
                else:
                    st.error("Please enter a valid YouTube URL")
            else:
                st.warning("Please enter a YouTube URL")

    # Add batch download section
    st.write('---')
    st.header('Batch Download')
    st.write('Paste a list of song/video prompts (one per line) to download the top result for each.')
    batch_prompts = st.text_area('Batch Prompts (one per line)', height=200)
    batch_format = st.selectbox('Format for Batch Download', ['MP3', 'MP4'], index=0)
    batch_quality = st.selectbox('Quality for Batch Download', ['320k', '128k', '96k'] if batch_format == 'MP3' else ['1080p', '720p', '480p', '360p', 'Best'], index=0)
    if st.button('Batch Download', type='primary'):
        if batch_prompts.strip():
            prompts = [line.strip() for line in batch_prompts.strip().split('\n') if line.strip()]
            st.info(f'Starting batch download for {len(prompts)} prompts...')
            for idx, prompt in enumerate(prompts, 1):
                st.write(f'**{idx}. {prompt}**')
                with st.spinner(f'Searching for "{prompt}"...'):
                    results = get_search_results(prompt, 1)
                if results and len(results) > 0:
                    video_id = results[0]['id']
                    st.write(f'Top result: {results[0]["title"]}')
                    download_media(video_id, batch_format, batch_quality)
                else:
                    st.warning('No results found for this prompt.')
        else:
            st.warning('Please enter at least one prompt for batch download.')

if __name__ == "__main__":
    main()
