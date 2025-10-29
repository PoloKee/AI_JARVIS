import os
import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from core.brain import Brain
from core.memory import Memory
from core.tts import speak
from core.speech import list_microphones, listen_with_vad, monitor_microphone_levels, transcribe_from_microphone
from core.settings import get_settings, update_settings, save_settings
from core import wakeword
from core.wakeword import WakeWordService
from drivers.system_info import get_system_info
from drivers.open_apps import open_application
from drivers.play_music import play_music


class JarvisGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jarvis AI")
        self.root.geometry("720x480")

        self.memory = Memory()
        self.brain = Brain(self.memory)
        self.wake_service = WakeWordService()
        self.settings = get_settings()

        # UI Elements
        self.input_label = tk.Label(root, text="Ask Jarvis:")
        self.input_label.pack(anchor="w", padx=12, pady=(12, 4))

        self.input_entry = tk.Entry(root)
        self.input_entry.pack(fill="x", padx=12)

        # Microphone selection
        self.mic_frame = tk.Frame(root)
        self.mic_frame.pack(fill="x", padx=12, pady=(4, 0))
        tk.Label(self.mic_frame, text="Microphone:").pack(side="left")
        self.mic_var = tk.StringVar()
        self._mic_label_to_index = {}
        self._populate_mic_dropdown()
        self.mic_menu = tk.OptionMenu(self.mic_frame, self.mic_var, *self._mic_options)
        self.mic_menu.pack(side="left", padx=6)

        # Microphone level meter and test button
        self.mic_level = ttk.Progressbar(self.mic_frame, orient="horizontal", mode="determinate", maximum=100, length=160)
        self.mic_level.pack(side="left", padx=8)
        self.test_mic_btn = tk.Button(self.mic_frame, text="Test Mic", command=self.test_microphone)
        self.test_mic_btn.pack(side="left", padx=4)

        self.buttons_frame = tk.Frame(root)
        self.buttons_frame.pack(fill="x", padx=12, pady=8)

        self.ask_btn = tk.Button(self.buttons_frame, text="Ask", command=self.ask)
        self.ask_btn.pack(side="left", padx=4)

        self.listen_btn = tk.Button(self.buttons_frame, text="Listen (Mic)", command=self.listen)
        self.listen_btn.pack(side="left", padx=4)

        self.speak_btn = tk.Button(self.buttons_frame, text="Speak Reply", command=self.speak_last)
        self.speak_btn.pack(side="left", padx=4)

        self.info_btn = tk.Button(self.buttons_frame, text="System Info", command=self.show_system_info)
        self.info_btn.pack(side="left", padx=4)

        self.open_notepad_btn = tk.Button(self.buttons_frame, text="Open Notepad", command=lambda: open_application("notepad"))
        self.open_notepad_btn.pack(side="left", padx=4)

        self.play_music_btn = tk.Button(self.buttons_frame, text="Play Music File", command=self.pick_and_play_music)
        self.play_music_btn.pack(side="left", padx=4)

        self.reload_env_btn = tk.Button(self.buttons_frame, text="Reload .env (Wake)", command=self.reload_env)
        self.reload_env_btn.pack(side="left", padx=4)

        # Settings panel launcher (wired later)
        self.settings_btn = tk.Button(self.buttons_frame, text="Settings", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=4)

        # Wake listener status
        self.wake_status_label = tk.Label(root, text="Wake Listener: Unknown")
        self.wake_status_label.pack(anchor="w", padx=12)

        self.output_label = tk.Label(root, text="Jarvis Output:")
        self.output_label.pack(anchor="w", padx=12, pady=(12, 4))

        self.output_text = tk.Text(root, height=14)
        self.output_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.last_reply = ""

        # Push-to-talk binding if enabled
        if self.settings.get("push_to_talk_enabled"):
            self.root.bind(f"<{self.settings.get('push_to_talk_key', 'F4')}>", lambda e: self.listen())

    def ask(self):
        query = self.input_entry.get().strip()
        if not query:
            messagebox.showinfo("Jarvis", "Please enter a question or command.")
            return
        reply = self.brain.process_input(query)
        self.last_reply = reply
        self._append_output(f"You: {query}\nJarvis: {reply}\n\n")

    def listen(self):
        def _task():
            try:
                # Determine selected device index
                sel = self.mic_var.get()
                device_index = self._mic_label_to_index.get(sel, None)
                # Use VAD if enabled, otherwise fallback
                if self.settings.get("vad_enabled", True):
                    text = listen_with_vad(
                        device_index=device_index,
                        aggressiveness=int(self.settings.get("vad_aggressiveness", 2)),
                        max_duration_sec=float(self.settings.get("max_duration_sec", 10.0)),
                        silence_ms=int(self.settings.get("silence_ms", 800)),
                        on_level=self._update_mic_level,
                    )
                else:
                    text = transcribe_from_microphone(device_index=device_index)
            except Exception as e:
                text = None
                messagebox.showerror("Microphone", f"Failed to capture audio: {e}")
            # Reset meter after capture
            self._update_mic_level(0)
            if text:
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, text)
                self.ask()
            else:
                self._append_output("(No speech captured)\n")

        threading.Thread(target=_task, daemon=True).start()

    def _update_mic_level(self, level: int):
        # Update progressbar safely from any thread
        try:
            self.root.after(0, lambda: self.mic_level.configure(value=max(0, min(100, int(level)))))
        except Exception:
            pass

    def test_microphone(self):
        def _task():
            try:
                sel = self.mic_var.get()
                device_index = self._mic_label_to_index.get(sel, None)
                ok = monitor_microphone_levels(device_index=device_index, duration_sec=3.0, on_level=self._update_mic_level)
                if not ok:
                    messagebox.showinfo("Microphone", "Mic level monitor unavailable. Ensure PyAudio is installed.")
            except Exception as e:
                messagebox.showerror("Microphone", f"Mic test failed: {e}")
            finally:
                self._update_mic_level(0)

        threading.Thread(target=_task, daemon=True).start()

    def _populate_mic_dropdown(self):
        """Populate microphone choices; include Auto option if none detected."""
        choices = list_microphones()
        options = ["Auto (default)"]
        mapping = {"Auto (default)": None}
        for idx, name in choices:
            label = f"[{idx}] {name}"
            options.append(label)
            mapping[label] = idx
        self._mic_options = options
        self._mic_label_to_index = mapping
        # Set default selection
        self.mic_var.set(options[0])

    def speak_last(self):
        if not self.last_reply:
            messagebox.showinfo("Jarvis", "No response to speak yet.")
            return
        threading.Thread(target=lambda: speak(self.last_reply), daemon=True).start()

    def show_system_info(self):
        info = get_system_info()
        self._append_output(f"System Info:\n{info}\n\n")

    def pick_and_play_music(self):
        file_path = filedialog.askopenfilename(title="Select music file", filetypes=[("Audio", "*.mp3 *.wav")])
        if file_path:
            threading.Thread(target=lambda: play_music(file_path), daemon=True).start()

    def _append_output(self, text: str):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def reload_env(self):
        try:
            # Restart wake listener to pick up updated .env
            self.wake_status_label.config(text="Wake Listener: Restarting...")
            started = self.wake_service.start(self.listen)
            status = "Running" if started and self.wake_service.is_running() else "Stopped"
            self.wake_status_label.config(text=f"Wake Listener: {status}")
            self._append_output(f"(Reloaded .env; wake listener {status.lower()})\n")
        except Exception as e:
            messagebox.showerror("Reload .env", f"Failed to restart wake listener: {e}")

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        s = self.settings

        # Variables
        vad_enabled_var = tk.BooleanVar(value=bool(s.get("vad_enabled", True)))
        wake_enabled_var = tk.BooleanVar(value=bool(s.get("wake_enabled", True)))
        ptt_enabled_var = tk.BooleanVar(value=bool(s.get("push_to_talk_enabled", False)))
        vad_aggr_var = tk.IntVar(value=int(s.get("vad_aggressiveness", 2)))
        silence_ms_var = tk.IntVar(value=int(s.get("silence_ms", 800)))
        max_dur_var = tk.DoubleVar(value=float(s.get("max_duration_sec", 10.0)))

        # Layout
        frm = tk.Frame(win)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Checkbutton(frm, text="Enable VAD (WebRTC)", variable=vad_enabled_var).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(frm, text="Enable Wake Word", variable=wake_enabled_var).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(frm, text="Enable Push-to-Talk (F4)", variable=ptt_enabled_var).grid(row=2, column=0, sticky="w")

        tk.Label(frm, text="VAD Aggressiveness (0-3)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        tk.Scale(frm, from_=0, to=3, orient="horizontal", variable=vad_aggr_var).grid(row=4, column=0, sticky="we")

        tk.Label(frm, text="Silence Tail (ms)").grid(row=5, column=0, sticky="w", pady=(8, 0))
        tk.Scale(frm, from_=100, to=1500, resolution=50, orient="horizontal", variable=silence_ms_var).grid(row=6, column=0, sticky="we")

        tk.Label(frm, text="Max Utterance Duration (sec)").grid(row=7, column=0, sticky="w", pady=(8, 0))
        tk.Scale(frm, from_=3, to=20, resolution=1, orient="horizontal", variable=max_dur_var).grid(row=8, column=0, sticky="we")

        btns = tk.Frame(win)
        btns.pack(fill="x", padx=12, pady=8)
        tk.Button(btns, text="Save", command=lambda: self._save_settings(win, vad_enabled_var.get(), wake_enabled_var.get(), ptt_enabled_var.get(), vad_aggr_var.get(), silence_ms_var.get(), max_dur_var.get())).pack(side="left")
        tk.Button(btns, text="Close", command=win.destroy).pack(side="right")

    def _save_settings(self, win, vad_enabled, wake_enabled, ptt_enabled, vad_aggr, silence_ms, max_dur):
        # Persist settings
        self.settings = update_settings({
            "vad_enabled": bool(vad_enabled),
            "wake_enabled": bool(wake_enabled),
            "push_to_talk_enabled": bool(ptt_enabled),
            "vad_aggressiveness": int(vad_aggr),
            "silence_ms": int(silence_ms),
            "max_duration_sec": float(max_dur),
        })
        save_settings(self.settings)

        # Apply wake listener state
        if self.settings.get("wake_enabled", True):
            started = self.wake_service.start(self.listen)
            status = "Running" if started and self.wake_service.is_running() else "Stopped"
        else:
            self.wake_service.stop()
            status = "Stopped"
        self.wake_status_label.config(text=f"Wake Listener: {status}")

        # Apply push-to-talk binding
        try:
            self.root.unbind(f"<{self.settings.get('push_to_talk_key', 'F4')}>")
        except Exception:
            pass
        if self.settings.get("push_to_talk_enabled"):
            self.root.bind(f"<{self.settings.get('push_to_talk_key', 'F4')}>", lambda e: self.listen())

        win.destroy()


def main():
    if load_dotenv:
        load_dotenv()
    root = tk.Tk()
    app = JarvisGUI(root)
    # Start wake word listener via service; activates microphone listening on detection
    if app.settings.get("wake_enabled", True):
        started = app.wake_service.start(app.listen)
        status = "Running" if started and app.wake_service.is_running() else "Stopped"
    else:
        status = "Stopped"
    app.wake_status_label.config(text=f"Wake Listener: {status}")
    root.mainloop()


if __name__ == "__main__":
    main()