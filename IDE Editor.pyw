import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import csv
import json
import copy
import logging
from dataclasses import dataclass, asdict, field

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

# --- Global Constants ---
FLAGS = [
    ("0", "(SA)Default", "No special flags"),
    ("1", "(SA)Render_Wet_Effects", "Object is rendered with wet effects"),
    ("2", "(SA)TOBJ_Night_Flag", "Object texture is used for night time"),
    ("4", "(SA)Alpha_Transparency_1", "Object has first type of transparency"),
    ("8", "(SA)Alpha_Transparency_2", "Object has second type of transparency"),
    ("16", "(SA)TOBJ_Day_Flag", "Object texture is used for day time"),
    ("32", "(SA)Interior_Object", "Object is an interior object"),
    ("64", "(SA)Disable_Shadow_Culling", "Object's shadow culling is disabled"),
    ("128", "(SA)Exclude_Surface_From_Culling", "Excludes object from surface culling"),
    ("129", "(SA)Render_Wet_Effect+", "Render_Wet_Effect Exclude_Surface_From_Culling+Unkown"),
    ("132", "(SA)Unkown", "Disable-backface-culling+Aplpha_Transparency_1+Unkown"),
    ("192", "(SA)Disable_Shadow_Culling+Exclude_Surface_From_Culling", "Excludes object from surface culling and disable shadow culling"),
    ("256", "(SA)Disable_Draw_Distance", "Disables the object's draw distance"),
    ("512", "(SA)Breakable_Window", "Object is a breakable window"),
    ("1024", "(SA)Breakable_Window_With_Cracks", "Breakable window with cracks"),
    ("2048", "(SA)Garage_door", "Object is a garage door"),
    ("2176", "(SA)Unkown", "Exclude_Surface_From_Culling+Unkown"),
    ("4096", "(SA)2-Clump-Object", "Object belongs to a clump"),
    ("4100", "(SA)Alpha_Transparency_1+Unkown", "Object has first type of transparency"),
    ("8192", "(SA)Small-Vegetation-Strong-wind-Effect", "Small vegetation affected by strong wind"),
    ("16384", "(SA)Standard-Vegetation", "Standard vegetation object"),
    ("32768", "(SA)Timecycle-PoleShadow-Flag", "Used in timecycle pole shadows"),
    ("32896", "Exclude_Surface_From_Culling+Unkown", "Exclude_Surface_From_Culling+Unkown"),
    ("65536", "(SA)Explosive", "Explosive object"),
    ("131072", "(SA)UNKNOWN-(Seems to be an SCM Flag)", "Uncertain flag, possibly an SCM flag"),
    ("262144", "(SA)UNKNOWN-(1 Object in Jizzy`s Club)", "Uncertain flag related to Jizzy's Club"),
    ("524288", "(SA)(SA)UNKNOWN-(?)", "Uncertain or unused flag"),
    ("1048576", "(SA)Graffiti", "Object is graffiti"),
    ("2097152", "(SA)Disable-backface-culling", "Disables backface culling"),
    ("2130048", "Exclude_Surface_From_Culling+Unkown", "Exclude_Surface_From_Culling+Unkown"),
    ("2097280", "(SA)Unkown", "Disable-backface-culling+Unkown"),
    ("2097284", "(SA)Unkown", "Disable-backface-culling+Aplpha_Transparency_1+Unkown"),
    ("2097156", "(SA)Unkown", "Object has second type of transparency+Unkown"),
    ("4194304", "(SA)UNKNOWN-Unused-(Parts of a statue in Atrium)", "Unused flag related to a statue"),
    ("1073741824", "(SA)Unknown", "An unknown flag")
]
IDE_COLUMNS = ("ID", "ModelName", "TextureName", "DrawDist", "Flags")
FLAGS_DICT = {int(item[0]): (item[1], item[2]) for item in FLAGS}


# --- Data Class for IDE Entries ---
@dataclass
class IDEEntry:
    ID: int
    ModelName: str
    TextureName: str
    DrawDist: float
    Flags: int

    def to_list(self):
        return [self.ID, self.ModelName, self.TextureName, self.DrawDist, self.Flags]


# --- Main Application Class ---
class IDEEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GTA SA IDE Editor")
        self.ide_data: list[IDEEntry] = []          # List of IDEEntry objects
        self.sort_orders = {}                       # Store sort order per column (True=ascending)
        self.current_file = None                    # Currently opened file path
        self.undo_stack: list[list[IDEEntry]] = []    # Undo stack storing lists of IDEEntry
        self.redo_stack: list[list[IDEEntry]] = []    # Redo stack for redo functionality
        self.unsaved_changes = False                # Flag to track unsaved changes

        self.create_widgets()
        self.bind_events()

    def bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind_all("<Control-z>", lambda e: self.undo())
        self.root.bind_all("<Control-y>", lambda e: self.redo())

    def on_closing(self):
        if self.unsaved_changes:
            if not messagebox.askokcancel("Quit", "You have unsaved changes. Quit anyway?"):
                return
        self.root.destroy()

    def create_widgets(self):
        self.create_menu()

        # --- Search & Filter Frame ---
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_tree())

        ttk.Label(search_frame, text="Filter by Flags:").pack(side=tk.LEFT, padx=5)
        flag_filter_values = ["All"] + [f"{f[0]} - {f[1]}" for f in FLAGS]
        self.flag_filter_combobox = ttk.Combobox(search_frame, values=flag_filter_values, state="readonly")
        self.flag_filter_combobox.current(0)
        self.flag_filter_combobox.pack(side=tk.LEFT, padx=5)
        self.flag_filter_combobox.bind("<<ComboboxSelected>>", lambda e: self.update_tree())

        ttk.Button(search_frame, text="Clear Filter", command=self.clear_filter).pack(side=tk.LEFT, padx=5)

        # --- Treeview Frame ---
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=IDE_COLUMNS, show="headings", selectmode="extended")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for col in IDE_COLUMNS:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_tree(_col))
            self.tree.column(col, width=100, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        # Right-click context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Status Bar ---
        self.status_label = ttk.Label(self.root, text="No entries loaded.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=(0, 5))

        # --- Buttons Frame ---
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Button(buttons_frame, text="Open IDE File", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Save IDE File", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Export to CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Export as JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)

        ttk.Label(buttons_frame, text="Start ID:").pack(side=tk.LEFT, padx=5)
        self.start_id_entry = ttk.Entry(buttons_frame, width=10)
        self.start_id_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Renumber IDs", command=self.renumber_ids).pack(side=tk.LEFT, padx=5)

        ttk.Button(buttons_frame, text="Add Entry", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Delete Entry", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Duplicate Entry", command=self.duplicate_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Bulk Edit", command=self.bulk_edit_entries).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Find & Replace", command=self.find_and_replace).pack(side=tk.LEFT, padx=5)

        # --- Edit Frame ---
        edit_frame = ttk.Frame(self.root)
        edit_frame.pack(fill=tk.X, pady=10, padx=5)
        ttk.Label(edit_frame, text="Model Name:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.model_name_entry = ttk.Entry(edit_frame)
        self.model_name_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(edit_frame, text="Texture Name:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.texture_name_entry = ttk.Entry(edit_frame)
        self.texture_name_entry.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)

        ttk.Label(edit_frame, text="Draw Distance:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.draw_dist_entry = ttk.Entry(edit_frame, width=10)
        self.draw_dist_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(edit_frame, text="Flags:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        flag_values = [f"{f[0]} - {f[1]}" for f in FLAGS]
        self.flag_combobox = ttk.Combobox(edit_frame, values=flag_values, state="readonly")
        self.flag_combobox.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        self.flag_combobox.bind("<<ComboboxSelected>>", self.update_flag_description)

        self.flag_description_label = ttk.Label(edit_frame, text="Flag Description: ")
        self.flag_description_label.grid(row=2, column=0, columnspan=4, padx=5, pady=2, sticky=tk.W)
        ttk.Button(edit_frame, text="Save Edits", command=self.save_edits).grid(row=3, column=0, columnspan=4, pady=5)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open IDE File", command=self.open_file)
        file_menu.add_command(label="Save IDE File", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_command(label="Export as JSON", command=self.export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find & Replace", command=self.find_and_replace)
        edit_menu.add_command(label="Bulk Edit", command=self.bulk_edit_entries)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo("About", "GTA SA IDE Editor\nVersion 2.0\nOptimized with Undo/Redo, new Find & Replace, Bulk Edit, JSON export, and context menus.")

    # --- File Operations ---

    def open_file(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Confirm", "You have unsaved changes. Continue and discard changes?"):
                return
        filepath = filedialog.askopenfilename(
            filetypes=[("IDE Files", "*.ide"), ("All Files", "*.*")]
        )
        if filepath:
            self.current_file = filepath
            self.ide_data = self.read_ide_file(filepath)
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.unsaved_changes = False
            self.update_tree()

    def read_ide_file(self, filepath) -> list[IDEEntry]:
        ide_data = []
        try:
            with open(filepath, "r") as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped or stripped.lower() in ("objs", "end"):
                        continue
                    parts = [part.strip() for part in stripped.split(",")]
                    if len(parts) in (5, 6):
                        try:
                            id_val = int(parts[0])
                            model = parts[1]
                            texture = parts[2]
                            # Determine order based on parts count
                            if len(parts) == 5:
                                drawdist = float(parts[3]) if parts[3] else 0.0
                                flag = int(parts[4]) if parts[4] else 0
                            else:
                                flag = int(parts[3]) if parts[3] else 0
                                drawdist = float(parts[4]) if parts[4] else 0.0
                            entry = IDEEntry(id_val, model, texture, drawdist, flag)
                            ide_data.append(entry)
                        except ValueError:
                            logging.warning("Skipping invalid line: %s", line)
                            continue
        except Exception as e:
            messagebox.showerror("Error", f"Error reading IDE file: {e}")
        return ide_data

    def save_file(self):
        if not self.current_file:
            self.current_file = filedialog.asksaveasfilename(
                defaultextension=".ide",
                filetypes=[("IDE Files", "*.ide"), ("All Files", "*.*")]
            )
            if not self.current_file:
                return
        self.write_ide_file(self.current_file)
        self.unsaved_changes = False

    def write_ide_file(self, filepath):
        try:
            with open(filepath, "w") as file:
                file.write("objs\n")
                for entry in self.ide_data:
                    file.write(f"{entry.ID}, {entry.ModelName}, {entry.TextureName}, {entry.DrawDist}, {entry.Flags}\n")
                file.write("end")
            messagebox.showinfo("Success", "File saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving IDE file: {e}")

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=IDE_COLUMNS)
                writer.writeheader()
                for entry in self.ide_data:
                    writer.writerow(asdict(entry))
            messagebox.showinfo("Success", "CSV file exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting CSV file: {e}")

    def export_json(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath, "w") as jsonfile:
                json.dump([asdict(entry) for entry in self.ide_data], jsonfile, indent=4)
            messagebox.showinfo("Success", "JSON file exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting JSON file: {e}")

    # --- Filtering, Sorting & Treeview Updates ---

    def clear_filter(self):
        self.search_entry.delete(0, tk.END)
        self.flag_filter_combobox.current(0)
        self.update_tree()

    def get_filtered_data(self):
        search_text = self.search_entry.get().lower().strip()
        flag_filter = self.flag_filter_combobox.get()
        filtered = []
        for idx, entry in enumerate(self.ide_data):
            if search_text and (search_text not in entry.ModelName.lower() and search_text not in entry.TextureName.lower()):
                continue
            if flag_filter != "All":
                try:
                    flag_value = int(flag_filter.split(" - ")[0])
                except ValueError:
                    continue
                if entry.Flags != flag_value:
                    continue
            filtered.append((idx, entry))
        return filtered

    def update_tree(self):
        self.tree.delete(*self.tree.get_children())
        filtered = self.get_filtered_data()
        for idx, entry in filtered:
            self.tree.insert("", "end", iid=str(idx), values=entry.to_list())
        self.status_label.config(text=f"Showing {len(filtered)} of {len(self.ide_data)} entries.")

    def sort_tree(self, col):
        ascending = self.sort_orders.get(col, True)
        self.sort_orders[col] = not ascending

        try:
            if col in ("ID", "DrawDist", "Flags"):
                self.ide_data.sort(key=lambda x: float(getattr(x, col)), reverse=not ascending)
            else:
                self.ide_data.sort(key=lambda x: getattr(x, col).lower(), reverse=not ascending)
        except Exception as e:
            messagebox.showerror("Error", f"Error sorting by {col}: {e}")
            return
        self.update_tree()

    # --- Editing and Flag Description ---
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
        except ValueError:
            return
        entry = self.ide_data[idx]
        self.model_name_entry.delete(0, tk.END)
        self.model_name_entry.insert(0, entry.ModelName)
        self.texture_name_entry.delete(0, tk.END)
        self.texture_name_entry.insert(0, entry.TextureName)
        self.draw_dist_entry.delete(0, tk.END)
        self.draw_dist_entry.insert(0, entry.DrawDist)
        flag_name = self.get_flag_name(entry.Flags)
        self.flag_combobox.set(f"{entry.Flags} - {flag_name}")
        self.update_flag_description(None)

    def get_flag_name(self, flag_value):
        return FLAGS_DICT.get(flag_value, ("Unknown", "No description available"))[0]

    def update_flag_description(self, event):
        flag_text = self.flag_combobox.get()
        try:
            flag_value = int(flag_text.split(" - ")[0])
        except ValueError:
            self.flag_description_label.config(text="Flag Description: Unknown")
            return
        desc = FLAGS_DICT.get(flag_value, ("Unknown", "No description available"))[1]
        self.flag_description_label.config(text=f"Flag Description: {desc}")

    def save_edits(self):
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
        except ValueError:
            return

        self.push_undo_state()

        model_name = self.model_name_entry.get().strip()
        texture_name = self.texture_name_entry.get().strip()
        try:
            draw_dist = float(self.draw_dist_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid draw distance. Please enter a number.")
            return
        flag_text = self.flag_combobox.get()
        try:
            flag = int(flag_text.split(" - ")[0])
        except ValueError:
            flag = 0

        # Update the IDEEntry object
        self.ide_data[idx].ModelName = model_name
        self.ide_data[idx].TextureName = texture_name
        self.ide_data[idx].DrawDist = draw_dist
        self.ide_data[idx].Flags = flag

        self.tree.item(selected[0], values=self.ide_data[idx].to_list())
        messagebox.showinfo("Info", "Entry updated successfully.")
        self.unsaved_changes = True

    # --- Undo/Redo Functionality ---
    def push_undo_state(self):
        self.undo_stack.append(copy.deepcopy(self.ide_data))
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.unsaved_changes = True

    def undo(self, event=None):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.ide_data))
            self.ide_data = self.undo_stack.pop()
            self.update_tree()
            messagebox.showinfo("Undo", "Reverted to previous state.")
            self.unsaved_changes = True
        else:
            messagebox.showinfo("Undo", "No more actions to undo.")

    def redo(self, event=None):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.ide_data))
            self.ide_data = self.redo_stack.pop()
            self.update_tree()
            messagebox.showinfo("Redo", "Redo successful.")
            self.unsaved_changes = True
        else:
            messagebox.showinfo("Redo", "No actions to redo.")

    # --- Entry Management ---
    def add_entry(self):
        self.push_undo_state()
        new_id = max((entry.ID for entry in self.ide_data), default=0) + 1
        new_entry = IDEEntry(new_id, "NewModel", "NewTexture", 0.0, 0)
        self.ide_data.append(new_entry)
        self.update_tree()
        messagebox.showinfo("Info", "New entry added.")

    def delete_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No entry selected for deletion.")
            return
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {len(selected)} entries?"):
            self.push_undo_state()
            indices = sorted([int(item) for item in selected], reverse=True)
            for idx in indices:
                del self.ide_data[idx]
            self.update_tree()
            messagebox.showinfo("Info", f"{len(indices)} entries deleted.")

    def duplicate_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No entry selected for duplication.")
            return
        try:
            idx = int(selected[0])
        except ValueError:
            return
        self.push_undo_state()
        orig = self.ide_data[idx]
        new_id = max((entry.ID for entry in self.ide_data), default=0) + 1
        new_entry = IDEEntry(new_id, orig.ModelName, orig.TextureName, orig.DrawDist, orig.Flags)
        self.ide_data.append(new_entry)
        self.update_tree()
        messagebox.showinfo("Info", "Entry duplicated.")

    def renumber_ids(self):
        try:
            self.push_undo_state()
            start_id = int(self.start_id_entry.get().strip())
            for i, entry in enumerate(self.ide_data):
                entry.ID = start_id + i
            self.update_tree()
        except ValueError:
            messagebox.showerror("Error", "Invalid ID. Please enter a valid number.")

    # --- New Feature: Bulk Edit ---
    def bulk_edit_entries(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No entries selected for bulk edit.")
            return

        # Ask for new ModelName as an example; extendable to other fields.
        new_model = simpledialog.askstring("Bulk Edit", "Enter new Model Name for selected entries:")
        if new_model is None:
            return

        self.push_undo_state()
        for sid in selected:
            try:
                idx = int(sid)
                self.ide_data[idx].ModelName = new_model
            except ValueError:
                continue
        self.update_tree()
        messagebox.showinfo("Bulk Edit", "Selected entries updated.")

    # --- New Feature: Find & Replace ---
    def find_and_replace(self):
        find_str = simpledialog.askstring("Find & Replace", "Find:")
        if find_str is None or find_str == "":
            return
        replace_str = simpledialog.askstring("Find & Replace", "Replace with:")
        if replace_str is None:
            return

        count = 0
        self.push_undo_state()
        for entry in self.ide_data:
            # Replace in ModelName and TextureName as an example.
            if find_str.lower() in entry.ModelName.lower():
                entry.ModelName = entry.ModelName.replace(find_str, replace_str)
                count += 1
            if find_str.lower() in entry.TextureName.lower():
                entry.TextureName = entry.TextureName.replace(find_str, replace_str)
                count += 1
        self.update_tree()
        messagebox.showinfo("Find & Replace", f"Replaced {count} occurrences.")

    # --- Context Menu for Treeview ---
    def show_context_menu(self, event):
        try:
            self.tree.selection_set(self.tree.identify_row(event.y))
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Duplicate Entry", command=self.duplicate_entry)
            menu.add_command(label="Delete Entry", command=self.delete_entry)
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


if __name__ == "__main__":
    root = tk.Tk()
    app = IDEEditor(root)
    root.mainloop()
