import os
import re
import threading
import requests
import tkinter as tk
from tkinter import filedialog, messagebox

# AniList GraphQL API endpoint and query
ANILIST_URL = "https://graphql.anilist.co"
ANILIST_QUERY = '''
query ($search: String) {
  Page(perPage: 10) {
    media(search: $search, type: ANIME) {
      id
      title {
        romaji
        english
      }
      startDate {
        year
      }
    }
  }
}
'''

def search_anime(query):
    """Call AniList API for a given query."""
    variables = {"search": query}
    try:
        response = requests.post(ANILIST_URL, json={'query': ANILIST_QUERY, 'variables': variables})
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("Page", {}).get("media", [])
    except Exception as e:
        print(f"[DEBUG] Error querying AniList for '{query}': {e}")
        return []

def sanitize_filename(name):
    """Remove invalid characters from a folder name."""
    invalid = r'<>:"/\|?*'
    for char in invalid:
        name = name.replace(char, '')
    return name.strip()

class AnimeFolderWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Anime Folder Wizard")
        self.geometry("800x600")
        
        # Directory and folder data
        self.directory = ""
        self.folders = []             # List of folder names (not full paths)
        self.folder_paths = {}        # Mapping: folder name -> full path
        self.folder_candidates = {}   # Mapping: folder name -> list of candidate anime dicts
        self.selected_candidates = {} # Mapping: folder name -> selected candidate index (or None)
        self.current_index = 0        # Index of the folder being processed
        self.current_candidates = []  # Candidates for the current folder
        
        # Checkbox variable to disregard text within () or [] (default: True)
        self.disregard_brackets_var = tk.BooleanVar(value=True)
        
        self.create_widgets()
    
    def create_widgets(self):
        # Top frame for directory selection, override search, and options
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.dir_btn = tk.Button(top_frame, text="Select Directory", command=self.select_directory)
        self.dir_btn.pack(side=tk.LEFT)
        
        self.dir_label = tk.Label(top_frame, text="No directory selected")
        self.dir_label.pack(side=tk.LEFT, padx=10)
        
        # Checkbox: Remove text inside () or [] (checked by default)
        self.checkbox = tk.Checkbutton(top_frame, text="Ignore text in () or []", variable=self.disregard_brackets_var)
        self.checkbox.pack(side=tk.LEFT, padx=10)
        
        # Custom search override entry
        override_label = tk.Label(top_frame, text="Custom Search Override:")
        override_label.pack(side=tk.LEFT, padx=5)
        self.override_search_entry = tk.Entry(top_frame)
        self.override_search_entry.pack(side=tk.LEFT, padx=5)
        
        # Frame to show current folder name
        self.folder_frame = tk.Frame(self)
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)
        self.folder_label = tk.Label(self.folder_frame, text="Folder:")
        self.folder_label.pack(side=tk.LEFT)
        
        # Candidate Selection Section inside a scrollable canvas.
        self.candidates_frame = tk.Frame(self, bd=2, relief=tk.SUNKEN)
        self.candidates_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.candidates_canvas = tk.Canvas(self.candidates_frame)
        self.candidates_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(self.candidates_frame, orient="vertical", command=self.candidates_canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.candidates_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.inner_candidates_frame = tk.Frame(self.candidates_canvas)
        self.candidates_canvas.create_window((0, 0), window=self.inner_candidates_frame, anchor="nw")
        self.inner_candidates_frame.bind("<Configure>", lambda e: self.candidates_canvas.configure(scrollregion=self.candidates_canvas.bbox("all")))
        
        # Bottom frame with a Skip Folder button.
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        self.skip_btn = tk.Button(bottom_frame, text="Skip Folder", command=self.skip_folder, state=tk.DISABLED)
        self.skip_btn.pack(padx=5, pady=5)
    
    def select_directory(self):
        folder = filedialog.askdirectory(title="Select Folder Containing Anime Folders")
        if folder:
            self.directory = folder
            self.dir_label.config(text=folder)
            self.load_folders()
    
    def load_folders(self):
        """Scan the selected directory for subfolders."""
        self.folders = []
        self.folder_paths = {}
        for item in os.listdir(self.directory):
            full_path = os.path.join(self.directory, item)
            if os.path.isdir(full_path):
                self.folders.append(item)
                self.folder_paths[item] = full_path
        if not self.folders:
            messagebox.showinfo("No Folders", "No subfolders found in the selected directory.")
            return
        self.current_index = 0
        self.selected_candidates = {}
        self.folder_candidates = {}
        self.show_current_folder()
    
    def show_current_folder(self):
        """Display the current folder and start fetching candidate anime."""
        if self.current_index >= len(self.folders):
            self.folder_label.config(text="All folders processed.")
            self.clear_candidates()
            self.skip_btn.config(state=tk.DISABLED)
            return
        
        folder_name = self.folders[self.current_index]
        self.folder_label.config(text=f"Folder: {folder_name}")
        self.clear_candidates()
        self.skip_btn.config(state=tk.NORMAL)
        threading.Thread(target=self.fetch_candidates, args=(folder_name,), daemon=True).start()
    
    def clear_candidates(self):
        for widget in self.inner_candidates_frame.winfo_children():
            widget.destroy()
        self.candidates_canvas.yview_moveto(0)
    
    def fetch_candidates(self, folder_name):
        """Fetch candidate anime using the entire folder name or custom override."""
        disregard = self.disregard_brackets_var.get()
        override_query = self.override_search_entry.get().strip()
        if override_query:
            query = override_query
        else:
            query = folder_name
            if disregard:
                query = re.sub(r"[\(\[].*?[\)\]]", "", query).strip()
        print(f"[DEBUG] Searching with query: '{query}'")
        candidates = search_anime(query)
        # Sort candidates by year (newest to oldest) and limit to top 5.
        if candidates:
            candidates = sorted(candidates, key=lambda anime: anime["startDate"].get("year") or 0, reverse=True)
            candidates = candidates[:5]
        self.current_candidates = candidates
        self.folder_candidates[folder_name] = candidates
        self.after(0, self.show_candidates)
    
    def show_candidates(self):
        """Display candidate anime as buttons in the inner candidates frame."""
        self.clear_candidates()
        if not self.current_candidates:
            lbl = tk.Label(self.inner_candidates_frame, text="No candidates found.")
            lbl.pack(pady=5)
            return
        
        lbl = tk.Label(self.inner_candidates_frame, text="Select the matching anime:")
        lbl.pack(pady=5)
        for idx, anime in enumerate(self.current_candidates):
            title = anime["title"]["english"] or anime["title"]["romaji"]
            year = anime["startDate"].get("year")
            text = f"{title} ({year})" if year else title
            btn = tk.Button(self.inner_candidates_frame, text=text,
                            command=lambda i=idx: self.candidate_selected(i))
            btn.pack(pady=2, fill=tk.X)
    
    def candidate_selected(self, index):
        """Store the candidate selection, rename the current folder, and move on."""
        folder_name = self.folders[self.current_index]
        self.selected_candidates[folder_name] = index
        new_name = self.get_new_name(folder_name)
        if not new_name:
            messagebox.showerror("Error", f"Could not determine new name for folder '{folder_name}'.")
            return
        old_path = self.folder_paths[folder_name]
        new_path = os.path.join(self.directory, new_name)
        if os.path.exists(new_path):
            messagebox.showerror("Conflict", f"Conflict on disk: '{new_name}' already exists.")
            return
        try:
            os.rename(old_path, new_path)
            print(f"[DEBUG] Renamed '{folder_name}' to '{new_name}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Error renaming folder '{folder_name}': {e}")
            return
        self.next_folder()
    
    def skip_folder(self):
        """Skip renaming the current folder and move to the next."""
        folder_name = self.folders[self.current_index]
        print(f"[DEBUG] Skipping folder '{folder_name}'.")
        self.next_folder()
    
    def next_folder(self):
        """Proceed to the next folder."""
        self.current_index += 1
        self.show_current_folder()
    
    def get_new_name(self, folder):
        """Construct the new folder name based on the selected candidate."""
        candidate_index = self.selected_candidates.get(folder)
        candidates = self.folder_candidates.get(folder, [])
        if candidate_index is None or candidate_index >= len(candidates):
            print(f"[DEBUG] No candidate selected for folder '{folder}'.")
            return None
        anime = candidates[candidate_index]
        title = anime["title"]["english"] or anime["title"]["romaji"]
        year = anime["startDate"].get("year")
        new_name = f"{title} ({year})" if year else title
        new_name = sanitize_filename(new_name)
        print(f"[DEBUG] Folder '{folder}' will be renamed to '{new_name}'.")
        return new_name

if __name__ == "__main__":
    app = AnimeFolderWizard()
    app.mainloop()
