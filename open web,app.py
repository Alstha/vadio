import os
import webbrowser
import streamlit as st

def execute_command(command):
    command = command.lower()

    # Open websites
    if "open youtube" in command:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube..."
    elif "open instagram" in command:
        webbrowser.open("https://instagram.com")
        return "Opening Instagram..."

    # Open folders
    elif "open downloads" in command:
        os.startfile(os.path.expanduser("~/Downloads"))
        return "Opening Downloads folder..."
    elif "open file explorer" in command:
        os.system("explorer")
        return "Opening File Explorer..."

    # Open software
    elif "open vs code" in command:
        os.startfile("C:/Users/alsth/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Cursor/Cursor.lnk")
        return "Opening VS Code..."

    else:
        return "Command not recognized"

# Streamlit UI
st.title("Command Executor")
st.write("Enter a command to execute various actions")

# Create a text input
command = st.text_input("Enter your command:")

# Create a button
if st.button("Execute"):
    if command:
        result = execute_command(command)
        st.write(result)
    else:
        st.warning("Please enter a command")

# Add some helpful examples
st.sidebar.title("Available Commands")
st.sidebar.write("""
- Open YouTube
- Open Instagram
- Open Downloads
- Open File Explorer
- Open VS Code
""")
