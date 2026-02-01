import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from auth_logic import (
    add_account,
    clear_cookie,
    delete_account,
    get_existing_cookie,
    get_full_cookie_file_content,
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
        self.geometry("720x480")
        self.minsize(680, 420)
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

        self.status_label = ctk.CTkLabel(controls, text="", justify="left")
        self.status_label.grid(row=8, column=0, sticky="ew", padx=12, pady=(16, 12))

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

    def open_add_popup(self) -> None:
        popup = ctk.CTkToplevel(self)
        popup.title("Add Account")
        popup.geometry("520x360")
        popup.grab_set()
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(2, weight=1)

        name_label = ctk.CTkLabel(popup, text="Nickname")
        name_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        name_entry = ctk.CTkEntry(popup, placeholder_text="Main")
        name_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        token_label = ctk.CTkLabel(popup, text=".ROBLOSECURITY Cookie")
        token_label.grid(row=2, column=0, sticky="nw", padx=16, pady=(0, 4))

        token_box = ctk.CTkTextbox(popup, height=140)
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
                name = f"Account {len(self.accounts) + 1}"
            add_account(name, token)
            popup.destroy()
            self.refresh_accounts()

        save_button = ctk.CTkButton(button_frame, text="Save", command=on_save)
        save_button.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=10)
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=10)

    def load_existing_account(self) -> None:
        result = get_full_cookie_file_content()
        if result.get("status") != "ok":
            messagebox.showerror("Load Existing", f"Could not find an existing cookie: {result}")
            return
        
        token = result.get("token", "")
        binary_data = result.get("data")
        
        dialog = ctk.CTkInputDialog(text="Nickname for existing account:", title="Load Existing")
        name = dialog.get_input()
        if not name:
            return
            
        add_account(name.strip(), token, binary_data)
        self.refresh_accounts()

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


def run() -> None:
    app = RobloxAccountManagerApp()
    app.mainloop()
