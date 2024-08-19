import tkinter as tk
from tkinter import filedialog, ttk
import fitz  # PyMuPDF
from PIL import Image, ImageTk


class PDFReader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Reader")

        self.zoom_factor = 1.0
        self.canvas_zoom_factor = 0.5  # Default 50% of display size
        self.justification = "center"  # Default justification
        self._drag_data = {"x": 0, "y": 0, "dragging": False}

        # Frame for the zoom controls
        self.zoom_control_frame = ttk.Frame(self)
        self.zoom_control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Navigation buttons on the left
        self.nav_control_frame = ttk.Frame(self.zoom_control_frame)
        self.nav_control_frame.pack(side=tk.LEFT)

        self.btn_previous = tk.Button(self.nav_control_frame, text="Previous", command=self.previous_page)
        self.btn_previous.pack(side=tk.LEFT, padx=5)

        self.btn_next = tk.Button(self.nav_control_frame, text="Next", command=self.next_page)
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Page number input and total pages display
        self.page_number_var = tk.StringVar()
        self.page_number_entry = tk.Entry(self.nav_control_frame, width=5, textvariable=self.page_number_var)
        self.page_number_entry.bind("<Return>", self.goto_page)
        self.page_number_entry.pack(side=tk.LEFT, padx=5)

        self.total_pages_label = tk.Label(self.nav_control_frame, text="/0")
        self.total_pages_label.pack(side=tk.LEFT)

        # Justification options
        self.justification_label = tk.Label(self.nav_control_frame, text="Justification:")
        self.justification_label.pack(side=tk.LEFT, padx=5)

        self.justification_var = tk.StringVar(value="Center")
        self.justification_options = ttk.Combobox(self.nav_control_frame, textvariable=self.justification_var,
                                                  values=["Left", "Center", "Right"], width=7)
        self.justification_options.pack(side=tk.LEFT, padx=5)
        self.justification_options.bind("<<ComboboxSelected>>", self.update_justification)

        # Zoom controls on the right
        self.zoom_controls_frame = ttk.Frame(self.zoom_control_frame)
        self.zoom_controls_frame.pack(side=tk.RIGHT)

        # Canvas zoom control
        self.canvas_zoom_label = tk.Label(self.zoom_controls_frame, text="Canvas Zoom:")
        self.canvas_zoom_label.pack(side=tk.LEFT)

        self.canvas_zoom_entry = tk.Entry(self.zoom_controls_frame, width=5)
        self.canvas_zoom_entry.insert(0, "50%")  # Default 50% zoom
        self.canvas_zoom_entry.bind("<Return>", self.update_canvas_zoom)
        self.canvas_zoom_entry.pack(side=tk.LEFT, padx=5)

        self.btn_zoom_out = tk.Button(self.zoom_controls_frame, text="-", command=self.zoom_out)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=5)

        self.zoom_entry = tk.Entry(self.zoom_controls_frame, width=5)
        self.zoom_entry.insert(0, "100%")  # Default zoom level is 100%
        self.zoom_entry.bind("<Return>", self.update_zoom)  # Update zoom when pressing Enter
        self.zoom_entry.pack(side=tk.LEFT, padx=5)

        self.btn_zoom_in = tk.Button(self.zoom_controls_frame, text="+", command=self.zoom_in)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=5)

        # Set up scrollbars and canvas inside a frame
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Horizontal scrollbar at the top
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas_xview)
        self.h_scrollbar.pack(side=tk.TOP, fill=tk.X)

        self.canvas = tk.Canvas(self.canvas_frame, bg="lightgrey")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        self.pdf_file = None
        self.current_page = 0
        self.pages = []

        self.menu = tk.Menu(self)
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.file_menu.add_command(label="Open", command=self.open_file)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.config(menu=self.menu)

        # Set initial canvas and window size based on canvas zoom
        self.update_canvas_zoom()

        # Bind mouse events only to the canvas
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Control-Button-1>", self.on_ctrl_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mouse_wheel)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)

    def canvas_xview(self, *args):
        self.canvas.xview(*args)

    def on_button_press(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["dragging"] = False

    def on_mouse_drag(self, event):
        delta_x = event.x - self._drag_data["x"]
        self.canvas.xview_scroll(int(-delta_x / 2), "units")
        self._drag_data["x"] = event.x
        self._drag_data["dragging"] = True

    def on_button_release(self, event):
        if not self._drag_data["dragging"] and not (event.state & 0x0004):  # Ctrl key pressed state check
            self.next_page()

    def on_ctrl_click(self, event):
        if not self._drag_data["dragging"]:
            self.previous_page()

    def open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filepath:
            self.load_pdf(filepath)
            self.adjust_window_size()

    def load_pdf(self, filepath):
        # Open PDF file with PyMuPDF
        self.pdf_file = fitz.open(filepath)
        self.pages = [page for page in self.pdf_file]
        self.total_pages_label.config(text=f"/{len(self.pages)}")
        self.show_page(0)

    def render_page(self, page):
        zoom_matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=zoom_matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return ImageTk.PhotoImage(img)

    def show_page(self, page_num):
        self.current_page = page_num
        self.page_number_var.set(str(page_num + 1))  # Set the current page in the entry box
        self.canvas.delete("all")
        image = self.render_page(self.pages[page_num])

        # Calculate horizontal positioning based on justification
        canvas_width = self.canvas.winfo_width()
        if self.justification.lower() == "left":
            image_x = 0
        elif self.justification.lower() == "right":
            image_x = max(canvas_width - image.width(), 0)
        else:  # Center
            image_x = max((canvas_width - image.width()) // 2, 0)

        # Ensure the canvas scroll region is set properly
        self.canvas.create_image(image_x, 0, anchor=tk.NW, image=image)
        self.canvas.config(scrollregion=(0, 0, max(image.width(), canvas_width), image.height()))

        self.image = image  # Keep a reference to prevent garbage collection

    def update_canvas_zoom(self, event=None):
        try:
            zoom_value = float(self.canvas_zoom_entry.get().strip('%'))
            if 20 <= zoom_value <= 80:  # Limiting zoom from 20% to 80%
                self.canvas_zoom_factor = zoom_value / 100
                self.set_canvas_size()
        except ValueError:
            pass  # Ignore invalid input

    def set_canvas_size(self):
        display_width = int(self.winfo_screenwidth() * self.canvas_zoom_factor)
        display_height = int(self.winfo_screenheight() * self.canvas_zoom_factor)
        self.canvas.config(width=display_width, height=display_height)
        self.update_idletasks()
        self.geometry(
            f"{display_width + self.v_scrollbar.winfo_width() + 20}x{display_height + self.zoom_control_frame.winfo_height() + self.h_scrollbar.winfo_height() + 20}")

    def adjust_window_size(self):
        self.update_idletasks()
        screen_height = self.winfo_screenheight()
        page_aspect_ratio = 11 / 8.5  # Assuming a standard page aspect ratio

        # Calculate desired height based on the screen height and aspect ratio
        desired_height = int(screen_height * 0.8)  # Adjust to 80% of the screen height
        desired_width = int(desired_height / page_aspect_ratio)

        # Ensure the app window fits within the screen boundaries
        current_width = max(self.winfo_width(), desired_width)
        self.geometry(f"{current_width}x{desired_height}")

    def zoom_in(self):
        self.zoom_factor += 0.05  # 5% increments
        self.update_zoom_entry()
        self.show_page(self.current_page)

    def zoom_out(self):
        if self.zoom_factor > 0.05:
            self.zoom_factor -= 0.05  # 5% increments
            self.update_zoom_entry()
            self.show_page(self.current_page)

    def update_zoom(self, event=None):
        try:
            zoom_value = float(self.zoom_entry.get().strip('%'))
            if zoom_value > 0:
                self.zoom_factor = zoom_value / 100
                self.show_page(self.current_page)
        except ValueError:
            pass  # Ignore invalid input

    def update_zoom_entry(self):
        self.zoom_entry.delete(0, tk.END)
        self.zoom_entry.insert(0, f"{int(self.zoom_factor * 100)}%")

    def next_page(self):
        if self.pdf_file and self.current_page < len(self.pages) - 1:
            self.show_page(self.current_page + 1)

    def previous_page(self):
        if self.pdf_file and self.current_page > 0:
            self.show_page(self.current_page - 1)

    def goto_page(self, event=None):
        try:
            page_num = int(self.page_number_var.get()) - 1
            if 0 <= page_num < len(self.pages):
                self.show_page(page_num)
        except ValueError:
            pass  # Ignore invalid input

    def update_justification(self, event=None):
        self.justification = self.justification_var.get().lower()
        self.show_page(self.current_page)

    def on_ctrl_click(self, event):
        if not self._drag_data["dragging"]:
            self.previous_page()

    def on_mouse_wheel(self, event):
        if event.state & 0x0004:  # Check if Ctrl is pressed
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def on_ctrl_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()


if __name__ == "__main__":
    app = PDFReader()
    app.mainloop()
