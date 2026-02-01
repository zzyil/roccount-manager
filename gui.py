import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk

from auth_logic import (
    add_account,
    clear_cookie,
    delete_account,
    export_accounts_to_json,
    get_existing_cookie,
    get_full_cookie_file_content,
    get_roblox_username,
    import_accounts_from_json,
    kill_roblox_processes,
    list_running_roblox_processes,
    load_account_cookie,
    load_accounts,
    rename_account,
    set_last_selected_id,
    switch_account,
)


class RobloxAccountManagerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.title("Roblox Account Manager")
        self.geometry("720x600")
        self.minsize(680, 500)
        self.accounts = []
        self.last_selected_id = None
        self.selected_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(header, text="Roblox Account Manager", font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=12, pady=12)

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        list_frame = ctk.CTkFrame(body)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        list_header = ctk.CTkLabel(list_frame, text="Accounts", font=ctk.CTkFont(size=16, weight="bold"))
        list_header.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        self.listbox = tk.Listbox(list_frame, activestyle="none", height=8)
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Stats / Details Panel
        self.details_frame = ctk.CTkFrame(list_frame)
        self.details_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.details_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.details_frame, text="Expires:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.lbl_expires = ctk.CTkLabel(self.details_frame, text="-", anchor="w")
        self.lbl_expires.grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        controls = ctk.CTkFrame(body)
        controls.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
        controls.grid_columnconfigure(0, weight=1)

        self.add_button = ctk.CTkButton(controls, text="Add Account", command=self.open_add_popup)
        self.add_button.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self.load_button = ctk.CTkButton(controls, text="Load Existing", command=self.load_existing_account)
        self.load_button.grid(row=1, column=0, sticky="ew", padx=12, pady=8)

        self.rename_button = ctk.CTkButton(controls, text="Rename", command=self.rename_selected)
        self.rename_button.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        self.delete_button = ctk.CTkButton(controls, text="Delete", command=self.delete_selected)
        self.delete_button.grid(row=3, column=0, sticky="ew", padx=12, pady=8)

        # Separator
        separator = ctk.CTkFrame(controls, height=2, fg_color="gray50")
        separator.grid(row=4, column=0, sticky="ew", padx=12, pady=12)

        self.load_roblox_button = ctk.CTkButton(
            controls, text="Load into Roblox", command=self.load_into_roblox, fg_color="#2E7D32", hover_color="#1B5E20"
        )
        self.load_roblox_button.grid(row=5, column=0, sticky="ew", padx=12, pady=8)

        self.switch_button = ctk.CTkButton(controls, text="Switch and Launch", command=self.switch_selected)
        self.switch_button.grid(row=6, column=0, sticky="ew", padx=12, pady=8)

        self.clear_cookie_button = ctk.CTkButton(
            controls, text="Clear Current Cookie", command=self.clear_current_cookie, fg_color="#C62828", hover_color="#8E0000"
        )
        self.clear_cookie_button.grid(row=7, column=0, sticky="ew", padx=12, pady=8)

        # Data Management
        data_frame = ctk.CTkFrame(controls, fg_color="transparent")
        data_frame.grid(row=8, column=0, sticky="ew", padx=12, pady=4)
        data_frame.grid_columnconfigure(0, weight=1)
        data_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_export = ctk.CTkButton(data_frame, text="Export", command=self.export_data)
        self.btn_export.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        
        self.btn_import = ctk.CTkButton(data_frame, text="Import", command=self.import_data)
        self.btn_import.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.status_label = ctk.CTkLabel(controls, text="", justify="left")
        self.status_label.grid(row=9, column=0, sticky="ew", padx=12, pady=(16, 12))

        self.refresh_accounts()

    def refresh_accounts(self) -> None:
        self.accounts, self.last_selected_id = load_accounts()
        self.listbox.delete(0, tk.END)
        for acc in self.accounts:
            self.listbox.insert(tk.END, acc.name)
        if self.last_selected_id:
            for idx, acc in enumerate(self.accounts):
                if acc.id == self.last_selected_id:
                    self.listbox.selection_set(idx)
                    self.selected_id = acc.id
                    break

    def on_select(self, _event) -> None:
        selection = self.listbox.curselection()
        if not selection:
            self.selected_id = None
            return
        idx = selection[0]
        self.selected_id = self.accounts[idx].id
        set_last_selected_id(self.selected_id)
        
        # Update details
        acc = self.accounts[idx]
        
        if acc.expires_at:
            from datetime import datetime
            dt = datetime.fromtimestamp(acc.expires_at)
            self.lbl_expires.configure(text=dt.strftime("%Y-%m-%d %H:%M"))
            
            # Check for expiry
            if acc.expires_at < datetime.now().timestamp():
                self.lbl_expires.configure(text_color="red")
            else:
                self.lbl_expires.configure(text_color=["black", "white"])
        else:
            self.lbl_expires.configure(text="Unknown")
            self.lbl_expires.configure(text_color=["black", "white"])



    def load_existing_account(self) -> None:
        result = get_full_cookie_file_content()
        if result.get("status") != "ok":
            messagebox.showerror("Load Existing", f"Could not find an existing cookie: {result}")
            return
        
        token = result.get("token", "")
        binary_data = result.get("data")
        
        # Auto-fetch username if token exists
        default_name = ""
        if token:
            fetched_name = get_roblox_username(token)
            if fetched_name:
                default_name = fetched_name
        
        self.open_add_popup(prefill_name=default_name, prefill_token=token, prefill_binary=binary_data)
        
    def open_add_popup(self, prefill_name: str = "", prefill_token: str = "", prefill_binary: bytes = None) -> None:
        popup = ctk.CTkToplevel(self)
        popup.title("Add Account")
        popup.geometry("520x360")
        popup.grab_set()
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(2, weight=1)

        name_label = ctk.CTkLabel(popup, text="Nickname")
        name_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        name_entry = ctk.CTkEntry(popup, placeholder_text="Main")
        name_entry.insert(0, prefill_name)
        name_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        token_label = ctk.CTkLabel(popup, text=".ROBLOSECURITY Cookie")
        token_label.grid(row=2, column=0, sticky="nw", padx=16, pady=(0, 4))

        token_box = ctk.CTkTextbox(popup, height=140)
        token_box.insert("1.0", prefill_token)
        token_box.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))

        button_frame = ctk.CTkFrame(popup)
        button_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        def on_save() -> None:
            name = name_entry.get().strip()
            token = token_box.get("1.0", "end").strip()
            if not token:
                messagebox.showerror("Missing Cookie", "Please paste a .ROBLOSECURITY cookie value.")
                return
            if not name:
                # Fallback to auto-fetch if user cleared it but token is there? Or just create default
                name = get_roblox_username(token) or f"Account {len(self.accounts) + 1}"
                
            add_account(name, token, prefill_binary) # Pass binary data if available
            popup.destroy()
            self.refresh_accounts()

        save_button = ctk.CTkButton(button_frame, text="Save", command=on_save)
        save_button.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=10)
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=10)

    def rename_selected(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Select Account", "Please select an account to rename.")
            return
        current = next((acc for acc in self.accounts if acc.id == self.selected_id), None)
        if not current:
            return
        dialog = ctk.CTkInputDialog(text="New nickname:", title="Rename Account")
        new_name = dialog.get_input()
        if not new_name:
            return
        rename_account(self.selected_id, new_name.strip())
        self.refresh_accounts()

    def delete_selected(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Select Account", "Please select an account to delete.")
            return
        current = next((acc for acc in self.accounts if acc.id == self.selected_id), None)
        if not current:
            return
        confirm = messagebox.askyesno("Delete Account", f"Delete {current.name}?")
        if not confirm:
            return
        delete_account(self.selected_id)
        self.selected_id = None
        self.refresh_accounts()

    def ensure_roblox_closed(self) -> bool:
        running = list_running_roblox_processes()
        if not running:
            return True
        
        confirm = messagebox.askyesno(
            "Roblox is Running",
            "Roblox is currently running. Changing accounts requires closing the game.\n\nClose Roblox now?",
        )
        if confirm:
            self.status_label.configure(text="Closing Roblox...")
            self.update_idletasks()
            kill_roblox_processes()
            self.status_label.configure(text="")
            return True
        return False

    def switch_selected(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Select Account", "Please select an account to switch to.")
            return
            
        if not self.ensure_roblox_closed():
            return
            
        self.status_label.configure(text="Switching account...")
        self.update_idletasks()
        result = switch_account(self.selected_id)
        inject_status = result.get("inject", {}).get("status")
        launch_status = result.get("launch", {}).get("status")
        if inject_status != "ok" or launch_status != "ok":
            messagebox.showerror("Switch Error", f"Switch status: {result}")
        else:
            messagebox.showinfo("Switched", "Account switched and Roblox launched.")
        self.status_label.configure(text="")

    def load_into_roblox(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Select Account", "Please select an account to load.")
            return
            
        if not self.ensure_roblox_closed():
            return
            
        current = next((acc for acc in self.accounts if acc.id == self.selected_id), None)
        if not current:
            return
        self.status_label.configure(text="Loading cookie...")
        self.update_idletasks()
        result = load_account_cookie(self.selected_id)
        if result.get("status") == "ok":
            messagebox.showinfo(
                "Cookie Loaded",
                f"Cookie for '{current.name}' has been loaded.\n\nYou can now launch Roblox manually.",
            )
        else:
            messagebox.showerror("Load Error", f"Failed to load cookie: {result}")
        self.status_label.configure(text="")

    def clear_current_cookie(self) -> None:
        if not self.ensure_roblox_closed():
            return

        confirm = messagebox.askyesno(
            "Clear Cookie",
            "Are you sure you want to clear the current Roblox cookie?\n\nThis will log you out of Roblox.",
        )
        if not confirm:
            return
        self.status_label.configure(text="Clearing cookie...")
        self.update_idletasks()
        result = clear_cookie()
        if result.get("status") == "ok":
            messagebox.showinfo("Cookie Cleared", "The Roblox cookie has been cleared successfully.")
        elif result.get("status") == "not_found":
            messagebox.showinfo("No Cookie", "No Roblox cookie was found to clear.")
        else:
            messagebox.showerror("Clear Error", f"Failed to clear cookie: {result}")
        self.status_label.configure(text="")


    def export_data(self) -> None:
        if not self.accounts:
            messagebox.showinfo("Export", "No accounts to export.")
            return
            
        proceed = messagebox.askyesno(
            "SECURITY WARNING",
            "This will export all your accounts including SENSITIVE COOKIES to a plain JSON file.\n\n"
            "ANYONE with this file can access your Roblox accounts!\n\n"
            "Do NOT share this file. Do you want to proceed?"
        )
        if not proceed:
            return
            
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Export Accounts (SENSITIVE)"
        )
        if not path:
            return
            
        try:
            from pathlib import Path
            export_accounts_to_json(Path(path))
            messagebox.showinfo("Export Successful", f"Successfully exported {len(self.accounts)} accounts.")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


    def import_data(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            title="Import Accounts"
        )
        if not path:
            return
        
        try:
            from pathlib import Path
            count = import_accounts_from_json(Path(path))
            messagebox.showinfo("Import Successful", f"Successfully imported {count} accounts.")
            self.refresh_accounts()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))


def run() -> None:
    app = RobloxAccountManagerApp()
    app.mainloop()
