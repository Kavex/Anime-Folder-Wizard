![image](https://github.com/user-attachments/assets/73a401aa-3ba3-4785-adf1-b502e088de83)

# Anime Folder Wizard

Anime Folder Wizard is a Python GUI tool that helps you organize your anime collection by automatically renaming your folders based on matching candidates from the AniList API. The tool uses the entire folder name as the search query—with an option to ignore any text within parentheses `()` or square brackets `[]`—and displays only the top 5 most likely matches. You can also override the search query manually with a custom string if needed.

## Features

- **Automatic Folder Renaming:**  
  Renames folders to the candidate's title and start year (formatted as `Title (Year)`).

- **Custom Search Override:**  
  Use the custom search entry to provide your own search string instead of using the folder name.

- **Ignore Extraneous Text:**  
  The "Ignore text in () or []" checkbox (checked by default) removes any text within parentheses or square brackets from the folder name before performing the search.

- **Top 5 Results:**  
  Displays only the top 5 candidates (sorted by start year, newest first) from the AniList API.

- **User-Friendly GUI:**  
  Built with Tkinter, featuring a scrollable candidate list and simple navigation options like skipping a folder.

## Prerequisites

- **Python 3.x**

- **Requests Library**  
  Install using pip:

  ```bash
  pip install requests

