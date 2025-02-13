import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Sample list of flags for dropdown
FLAGS = [
    ("0", "(SA)Default", "No special flags"),
    ("1", "(SA)Render_Wet_Effects", "Object is rendered with wet effects"),
    ("2", "(SA)TOBJ_Night_Flag", "Object texture is used for night time"),
    ("16", "(SA)TOBJ_Day_Flag", "Object texture is used for day time"),
    ("4", "(SA)Alpha_Transparency_1", "Object has first type of transparency"),
    ("8", "(SA)Alpha_Transparency_2", "Object has second type of transparency"),
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
    ("8192", "(SA)Small-Vegetation-Strong-wind-Effect", "Small vegetation affected by strong wind"),
    ("16384", "(SA)Standard-Vegetation", "Standard vegetation object"),
    ("32768", "(SA)Timecycle-PoleShadow-Flag", "Used in timecycle pole shadows"),
    ("65536", "(SA)Explosive", "Explosive object"),
    ("131072", "(SA)UNKNOWN-(Seems to be an SCM Flag)", "Uncertain flag, possibly an SCM flag"),
    ("262144", "(SA)UNKNOWN-(1 Object in Jizzy`s Club)", "Uncertain flag related to Jizzy's Club"),
    ("524288", "(SA)(SA)UNKNOWN-(?)", "Uncertain or unused flag"),
    ("1048576", "(SA)Graffiti", "Object is graffiti"),
    ("2097152", "(SA)Disable-backface-culling", "Disables backface culling"),
    ("2097280", "(SA)Unkown", "Disable-backface-culling+Unkown"),
    ("2097284", "(SA)Unkown", "Disable-backface-culling+Aplpha_Transparency_1+Unkown"),
    ("2097156", "(SA)Unkown", "Object has second type of transparency+Unkown"),
    ("4194304", "(SA)UNKNOWN-Unused-(Parts of a statue in Atrium)", "Unused flag related to a statue"),
    ("1073741824", "(SA)Unknown", "An unknown flag")
]

class IDEEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GTA SA IDE Editor")

        # The complete list of IDE data entries.
        self.ide_data = []

        self.create_widgets()

    def create_widgets(self):
        # === Search & Filter Frame ===
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", lambda event: self.update_tree())

        ttk.Label(search_frame, text="Filter by Flags:").pack(side=tk.LEFT, padx=5)
        flag_filter_values = ["All"] + [f"{f[0]} - {f[1]}" for f in FLAGS]
        self.flag_filter_combobox = ttk.Combobox(search_frame, values=flag_filter_values, state="readonly")
        self.flag_filter_combobox.current(0)
        self.flag_filter_combobox.pack(side=tk.LEFT, padx=5)
        self.flag_filter_combobox.bind("<<ComboboxSelected>>", lambda event: self.update_tree())

        # === Treeview Frame ===
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ID", "ModelName", "TextureName", "DrawDist", "Flags")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        for col in columns:
            self.tree.heading(col, text=col)

        # Bind selection to load data into edit fields.
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # === Buttons Frame ===
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(fill=tk.X, pady=10)

        ttk.Button(buttons_frame, text="Open IDE File", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Save IDE File", command=self.save_file).pack(side=tk.LEFT, padx=5)

        ttk.Label(buttons_frame, text="Start ID:").pack(side=tk.LEFT, padx=5)
        self.start_id_entry = ttk.Entry(buttons_frame, width=10)
        self.start_id_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Renumber IDs", command=self.renumber_ids).pack(side=tk.LEFT, padx=5)

        # === Edit Frame ===
        edit_frame = ttk.Frame(self.root)
        edit_frame.pack(fill=tk.X, pady=10)

        ttk.Label(edit_frame, text="Model Name:").pack(side=tk.LEFT, padx=5)
        self.model_name_entry = ttk.Entry(edit_frame)
        self.model_name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(edit_frame, text="Texture Name:").pack(side=tk.LEFT, padx=5)
        self.texture_name_entry = ttk.Entry(edit_frame)
        self.texture_name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(edit_frame, text="Draw Distance:").pack(side=tk.LEFT, padx=5)
        self.draw_dist_entry = ttk.Entry(edit_frame, width=10)
        self.draw_dist_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(edit_frame, text="Flags:").pack(side=tk.LEFT, padx=5)
        self.flag_combobox = ttk.Combobox(edit_frame,
                                          values=[f"{f[0]} - {f[1]}" for f in FLAGS],
                                          state="readonly")
        self.flag_combobox.pack(side=tk.LEFT, padx=5)

        ttk.Button(edit_frame, text="Save Edits", command=self.save_edits).pack(side=tk.LEFT, padx=5)

    def open_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("IDE Files", "*.ide"), ("All Files", "*.*")]
        )
        if filepath:
            self.ide_data = self.read_ide_file(filepath)
            self.update_tree()

    def read_ide_file(self, filepath):
        ide_data = []
        try:
            with open(filepath, "r") as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped or stripped.lower() in ("objs", "end"):
                        continue
                    parts = [part.strip() for part in stripped.split(",")]
                    if len(parts) != 5:
                        continue
                    ide_data.append({
                        "ID": int(parts[0]),
                        "ModelName": parts[1],
                        "TextureName": parts[2],
                        "DrawDist": float(parts[3]),
                        "Flags": int(parts[4])
                    })
        except Exception as e:
            messagebox.showerror("Error", f"Error reading IDE file: {e}")
        return ide_data

    def get_filtered_data(self):
        """
        Returns a list of tuples (index, data) from self.ide_data that match
        both the search text and the flag filter.
        """
        search_text = self.search_entry.get().lower().strip()
        flag_filter = self.flag_filter_combobox.get()
        filtered = []
        for idx, data in enumerate(self.ide_data):
            # Check search text against ModelName and TextureName.
            if search_text and (search_text not in data["ModelName"].lower() and
                                search_text not in data["TextureName"].lower()):
                continue

            # Check flag filter if not "All"
            if flag_filter != "All":
                try:
                    flag_value = int(flag_filter.split(" - ")[0])
                except ValueError:
                    continue
                if data["Flags"] != flag_value:
                    continue
            filtered.append((idx, data))
        return filtered

    def update_tree(self):
        """Clear the tree and reinsert data that passes current filters."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, data in self.get_filtered_data():
            # Use the original index as the item id.
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    data["ID"],
                    data["ModelName"],
                    data["TextureName"],
                    data["DrawDist"],
                    data["Flags"],
                ),
            )

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        # The tree item id is the original index in self.ide_data.
        try:
            idx = int(selected[0])
        except ValueError:
            return

        data = self.ide_data[idx]
        self.model_name_entry.delete(0, tk.END)
        self.model_name_entry.insert(0, data["ModelName"])

        self.texture_name_entry.delete(0, tk.END)
        self.texture_name_entry.insert(0, data["TextureName"])

        self.draw_dist_entry.delete(0, tk.END)
        self.draw_dist_entry.insert(0, data["DrawDist"])

        # Set the flag combobox using the stored flag value.
        flag_name = self.get_flag_name(data["Flags"])
        self.flag_combobox.set(f"{data['Flags']} - {flag_name}")

    def get_flag_name(self, flag_value):
        """
        Given a numeric flag_value, returns the human‑readable flag name.
        """
        for flag in FLAGS:
            try:
                if int(flag[0]) == flag_value:
                    return flag[1]
            except ValueError:
                continue
        return "Unknown"

    def save_edits(self):
        selected = self.tree.selection()
        if not selected:
            return

        try:
            idx = int(selected[0])
        except ValueError:
            return

        model_name = self.model_name_entry.get().strip()
        texture_name = self.texture_name_entry.get().strip()
        draw_dist = float(self.draw_dist_entry.get().strip())

        flag_text = self.flag_combobox.get()
        flag = int(flag_text.split(" - ")[0])

        # Update the underlying data.
        self.ide_data[idx].update({
            "ModelName": model_name,
            "TextureName": texture_name,
            "DrawDist": draw_dist,
            "Flags": flag
        })

        # Update the tree view item.
        self.tree.item(selected, values=(
            self.ide_data[idx]["ID"],
            model_name,
            texture_name,
            draw_dist,
            flag,
        ))
        messagebox.showinfo("Info", "Entry updated successfully.")

    def save_file(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".ide",
            filetypes=[("IDE Files", "*.ide"), ("All Files", "*.*")],
        )
        if filepath:
            self.write_ide_file(filepath)

    def write_ide_file(self, filepath):
        try:
            with open(filepath, "w") as file:
                file.write("objs\n")
                for data in self.ide_data:
                    file.write(f"{data['ID']}, {data['ModelName']}, {data['TextureName']}, {data['DrawDist']}, {data['Flags']}\n")
                file.write("end")
            messagebox.showinfo("Success", "File saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving IDE file: {e}")

    def renumber_ids(self):
        try:
            start_id = int(self.start_id_entry.get().strip())
            for i, data in enumerate(self.ide_data):
                data["ID"] = start_id + i
            self.update_tree()
        except ValueError:
            messagebox.showerror("Error", "Invalid ID. Please enter a number.")

if __name__ == "__main__":
    root = tk.Tk()
    app = IDEEditor(root)
    root.mainloop()
