"""'What KAIRO learned about how you speak': the words it listens for and the corrections it has learned.
Opened from the tray menu (as its own small window process) or with `--learned`.
Everything shown lives on this computer; it is sent to Prisma only as speech hints."""
from . import boost, memory


def load() -> dict:
    """What KAIRO has learned so far, for the window and for tests."""
    return {
        "words": boost.bias_words(),
        "corrections": memory.corrections(boost.MAX_RULES),
        "notes": len(memory.all_memories()),
    }


def remove_correction(wrong: str) -> None:
    memory.delete_correction(wrong)


def show(auto_close_ms: int | None = None) -> None:
    """The window. `auto_close_ms` is for tests only."""
    import tkinter as tk
    from tkinter import ttk

    BG, FG, PINK, MUTED = "#1a0b3d", "#ffffff", "#ff4fc3", "#c9bbe8"
    root = tk.Tk()
    root.title("KAIRO - what I learned about how you speak")
    root.geometry("660x600")
    root.minsize(560, 480)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
    style.configure("Head.TLabel", font=("Segoe UI", 16, "bold"), foreground=PINK)
    style.configure("Sub.TLabel", foreground=MUTED)
    style.configure("Sec.TLabel", font=("Segoe UI", 11, "bold"))
    style.configure("TButton", font=("Segoe UI", 10), padding=6)
    style.configure("Treeview", background="#2a1460", fieldbackground="#2a1460", foreground=FG, rowheight=30,
                    font=("Segoe UI", 11), borderwidth=0)
    style.configure("Treeview.Heading", background="#3b1796", foreground=FG, font=("Segoe UI", 10, "bold"))
    style.map("Treeview", background=[("selected", "#ff1fa8")])

    outer = ttk.Frame(root, padding=18)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="What I learned about how you speak", style="Head.TLabel").pack(anchor="w")
    ttk.Label(outer, wraplength=600, style="Sub.TLabel",
              text="This stays on your computer. I send it to Prisma only as hints, so I hear you better each time."
              ).pack(anchor="w", pady=(2, 12))

    corr_title = ttk.Label(outer, style="Sec.TLabel")
    corr_title.pack(anchor="w")
    tree = ttk.Treeview(outer, columns=("wrong", "right"), show="headings", height=6, selectmode="browse")
    tree.heading("wrong", text="Prisma writes")
    tree.heading("right", text="You mean")
    tree.column("wrong", width=280)
    tree.column("right", width=280)
    tree.pack(fill="x", pady=(4, 4))
    empty = ttk.Label(outer, style="Sub.TLabel", wraplength=600,
                      text="Nothing yet. When Prisma mishears a word in a note you save, I learn the fix.")

    words_title = ttk.Label(outer, style="Sec.TLabel")
    words_title.pack(anchor="w", pady=(14, 0))
    box = tk.Text(outer, height=9, wrap="word", bg="#2a1460", fg=FG, relief="flat", font=("Segoe UI", 11),
                  padx=10, pady=8, highlightthickness=0)
    box.pack(fill="both", expand=True, pady=(4, 8))

    def refresh() -> None:
        data = load()
        tree.delete(*tree.get_children())
        for wrong, right in data["corrections"]:
            tree.insert("", "end", iid=wrong, values=(wrong, right))
        corr_title.config(text=f"Corrections ({len(data['corrections'])} of {boost.MAX_RULES})")
        if data["corrections"]:
            empty.pack_forget()
        else:
            empty.pack(anchor="w", after=tree)
        words_title.config(text=f"Words I listen for ({len(data['words'])} of {boost.MAX_WORDS}), from {data['notes']} notes")
        box.config(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", "   •   ".join(data["words"]) if data["words"]
                   else "Nothing yet. Save a note and the important words appear here.")
        box.config(state="disabled")

    def remove_selected() -> None:
        picked = tree.selection()
        if picked:
            remove_correction(picked[0])
            refresh()

    buttons = ttk.Frame(outer)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Remove selected correction", command=remove_selected).pack(side="left")
    ttk.Button(buttons, text="Refresh", command=refresh).pack(side="left", padx=8)
    ttk.Button(buttons, text="Close", command=root.destroy).pack(side="right")

    refresh()
    if auto_close_ms:
        root.after(auto_close_ms, root.destroy)
    root.mainloop()
