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
        
        # Generate a unique filename
        timestamp = int(time.time())
        output_template = os.path.join(output_path, f"%(title)s_{timestamp}.%(ext)s")
        
        with st.spinner(f"Downloading {format_type} in {quality} quality..."):
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
                # Create the output filename
                ext = 'm4a' if format_type == 'MP3' else 'mp4'
                output_file = os.path.join(output_path, f"{title}_{timestamp}.{ext}")
                
                # Now download the file
                command = [
                    "yt-dlp",
                    f"https://www.youtube.com/watch?v={video_id}",
                    "--output", output_file,
                    "--no-playlist",
                    "--no-warnings",
                    "--quiet"
                ]
                
                # Add format-specific options
                if format_type == "MP3":
                    # Use direct audio format selection instead of post-processing
                    if quality == "320k":
                        command.extend(["--format", "bestaudio[ext=m4a]/bestaudio/best"])
                    else:
                        command.extend(["--format", "worstaudio[ext=m4a]/worstaudio/worst"])
                else:  # MP4
                    if quality == "Best":
                        command.extend(["--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
                    else:
                        command.extend(["--format", f"bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality[:-1]}][ext=mp4]/best"])
                
                # Download the file
                download_result = subprocess.run(command, capture_output=True, text=True)
                if download_result.returncode == 0:
                    if os.path.exists(output_file):
                        st.success(f"Successfully downloaded {format_type} in {quality} quality")
                        return output_file
                    else:
                        st.error(f"File not found at: {output_file}")
                        return None
                else:
                    st.error(f"Download failed: {download_result.stderr}")
                    return None
                    
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse video info: {str(e)}")
                return None
                
    except Exception as e:
        st.error(f"Error downloading {format_type}: {str(e)}")
        return None

def create_download_button(file_path, format_type):
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            st.download_button(
                label=f"Download {format_type}",
                data=file,
                file_name=os.path.basename(file_path),
                mime=f"audio/{format_type.lower()}" if format_type == "MP3" else "video/mp4"
            )

def format_duration(seconds):
    if not seconds:
        return "Unknown duration"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def main():
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
                    if st.button(f"Download {st.session_state['format']} ({st.session_state['quality']})", key=f"download_{i}"):
                        output_file = download_media(result['id'], st.session_state['format'], st.session_state['quality'])
                        if output_file:
                            create_download_button(output_file, st.session_state['format'])

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
        
        if st.button("Download", type="primary"):
            if url:
                if is_youtube_url(url):
                    video_id = extract_video_id(url)
                    if video_id:
                        output_file = download_media(video_id, st.session_state['format'], st.session_state['quality'])
                        if output_file:
                            create_download_button(output_file, st.session_state['format'])
                    else:
                        st.error("Invalid YouTube URL")
                else:
                    st.error("Please enter a valid YouTube URL")
            else:
                st.warning("Please enter a YouTube URL")

if __name__ == "__main__":
    main()
