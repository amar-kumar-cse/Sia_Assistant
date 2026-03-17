import customtkinter as ctk
import threading
import brain
import voice_engine
import actions
import listen_engine
from PIL import Image
import os

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class SiaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sia - Personal AI Assistant")
        self.geometry("900x700") # Increased width for image
        
        self.grid_columnconfigure(0, weight=1) # Chat Area
        self.grid_columnconfigure(1, weight=1) # Image Area
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # --- LEFT SIDE: Chat ---
        self.chat_frame = ctk.CTkFrame(self)
        self.chat_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.chat_frame, width=400, height=550, corner_radius=10)
        self.chat_display.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.chat_display.configure(state="disabled")
        
        # Input Area (inside Left Frame)
        self.input_frame = ctk.CTkFrame(self.chat_frame)
        self.input_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Amar: Kuch kaho...")
        self.entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        self.entry.bind("<Return>", self.on_enter_pressed)

        self.send_button = ctk.CTkButton(self.input_frame, text="Send", width=60, command=self.process_input)
        self.send_button.grid(row=0, column=1, padx=(5, 5), pady=10)

        self.mic_button = ctk.CTkButton(self.input_frame, text="🎤", width=40, command=self.start_listening, fg_color="red")
        self.mic_button.grid(row=0, column=2, padx=(5, 10), pady=10)

        # --- RIGHT SIDE: Character Image ---
        self.image_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.image_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        
        # Load Images
        self.load_character_images()
        
        self.character_label = ctk.CTkLabel(self.image_frame, text="", image=self.img_idle)
        self.character_label.pack(expand=True, fill="both")

        # Welcome Message
        self.append_message("Sia", "Namaste Hero! Kaisa hai mera dost? Kuch kaam hai ya bas baatein karni hain? ❤️")
        
        # Start Animation Loop
        self.check_animation_state()

    def load_character_images(self):
        # Placeholder logic: User should place 'sia_idle.png' and 'sia_talking.png' (or gif)
        # For now, we create a simple placeholder if not exists
        try:
            # Try to load existing images
            if os.path.exists("sia_talking.png"):
                 self.img_talking = ctk.CTkImage(light_image=Image.open("sia_talking.png"), size=(400, 400))
            else:
                 # Fallback to a placeholder color/shape if missing
                 self.img_talking = ctk.CTkImage(light_image=Image.new("RGB", (400, 400), (255, 100, 100)), size=(400, 400))
            
            if os.path.exists("sia_idle.png"):
                 self.img_idle = ctk.CTkImage(light_image=Image.open("sia_idle.png"), size=(400, 400))
            else:
                 self.img_idle = ctk.CTkImage(light_image=Image.new("RGB", (400, 400), (100, 100, 255)), size=(400, 400))
                 
        except Exception as e:
            print(f"Error loading images: {e}")
            self.img_talking = None
            self.img_idle = None

    def check_animation_state(self):
        """Checks if Sia is speaking and toggles the image."""
        if voice_engine.is_speaking:
            # Simple toggle effect for "animation" if using static images
            # Ideally we would play a GIF, but CTK doesn't support GIFs natively easily.
            # We can alternate images or just show the 'Talking' state.
            
            current_image = self.character_label.cget("image")
            new_image = self.img_talking if current_image == self.img_idle else self.img_idle
            
            # If we have a dedicated talking image that is different, use it.
            # For a GIF-like effect with 2 images, we can toggle.
            # If we just want to show "Mouth Open" while speaking, just show img_talking.
            
            # Let's try to simulate animation by toggling every 200ms
            self.character_label.configure(image=new_image)
            self.after(200, self.check_animation_state)
        else:
            # Revert to Idle
            self.character_label.configure(image=self.img_idle)
            self.after(500, self.check_animation_state)

    def append_message(self, sender, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"{sender}: {message}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def on_enter_pressed(self, event):
        self.process_input()

    def start_listening(self):
        self.mic_button.configure(state="disabled", text="...", fg_color="grey")
        threading.Thread(target=self.listen_thread).start()

    def listen_thread(self):
        text = listen_engine.listen()
        if text:
            self.entry.delete(0, "end")
            self.entry.insert(0, text)
            self.process_input()
        else:
            self.update_gui_message("System", "Could not hear anything.")
        self.mic_button.configure(state="normal", text="🎤", fg_color="red")

    def process_input(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.append_message("Amar", user_text)
        threading.Thread(target=self.backend_processing, args=(user_text,)).start()

    def backend_processing(self, user_text):
        action_result = actions.perform_action(user_text)
        if action_result:
            self.update_gui_message("Sia", f"(Action) {action_result}")
            # Run speak in a separate thread so it doesn't block this logic if we had more after
            # But here speak IS blocking in its own thread from the engine perspective? 
            # No, voice_engine.speak blocks. So we should run it.
            voice_engine.speak(f"Done Hero! {action_result}")
            return

        response = brain.think(user_text)
        self.update_gui_message("Sia", response)
        voice_engine.speak(response)

    def update_gui_message(self, sender, message):
        self.after(0, lambda: self.append_message(sender, message))

if __name__ == "__main__":
    app = SiaApp()
    app.mainloop()
