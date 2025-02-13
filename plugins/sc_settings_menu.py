import sys
import subprocess
import os
import gc
import shutil
from pathlib import Path
import numpy as np
from PyQt5.QtWidgets import QFileDialog

from phy import IPlugin, connect
from phylib.io.sc_params_dialog import ScParamsDialog
from phylib.io.sc_params import ScParams

def _edit_parameters(params:ScParams):
    updated_params, accepted = ScParamsDialog.edit_params(params)
    if accepted:
        return updated_params
    return None

def select_or_create_folder():
    folder_path = QFileDialog.getExistingDirectory(
        None,
        caption="Select Folder",
        directory=""
    )
    
    if folder_path:
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
    
    return None

def copy_files(source_dir, dest_dir):
    Path(dest_dir).mkdir(parents=True, exist_ok=True)    
    patterns = ['*.npy', '*.toml', '*.toml.backup']
    
    for root, _, files in os.walk(source_dir):
        for pattern in patterns:
            for filepath in Path(source_dir).glob(pattern):
                dest_path = os.path.join(dest_dir, filepath.name)
                shutil.copy2(filepath, dest_path)

# Close all data files so the won't be locked from access by other applications
def close_all_open_files():
    for obj in gc.get_objects():
        if isinstance(obj, np.ndarray) and hasattr(obj, '_mmap') and obj._mmap is not None:
            try:
                obj._mmap.close()
            except Exception as e:
                print(f"Failed to close {obj._mmap.filename}: {e}")

class ScSettingsMenuPlugin(IPlugin):
    def attach_to_controller(self, controller):
        @connect
        def on_gui_ready(sender, gui):
            gui.file_actions.separator()
            @gui.file_actions.add(toolbar=True) # Use icon 'f1de'
            def sc_settings():
                params = controller.sc_params
                if updated_params := _edit_parameters(params):
                    for key in updated_params:
                        params[key] = updated_params[key]

            @gui.file_actions.add(toolbar=True)
            def backup_project():
                script_dir = os.path.dirname(controller.sc_params.main.script_path)
                abs_folder_path = script_dir + "/" + controller.sc_params.output_dir
                new_folder_path = select_or_create_folder()
                if new_folder_path:
                    copy_files(abs_folder_path, new_folder_path)

            @gui.file_actions.add(toolbar=True)
            def run_sc_sort():
                close_all_open_files()

                start_point = "spike-detection"
                end_point = "save-to-phy"
                params = controller.sc_params
                
                script_dir = os.path.dirname(params.main.script_path)
                n_threads = str(params.main.n_threads)
                output_dir = params.main.output_dir
                raw_data_file = params.main.raw_data_file
                start_time_s = str(int(params.main.frame_window_start / 30_000))
                t_duration_s = str(int(params.main.n_tot_frames/30_000))

                # Set numnber of threads
                os.environ["JULIA_NUM_THREADS"] = n_threads

                # Because -l flag is enabled, all parameters in params object will be 
                # automatically loaded when script is called. 
                #   -d argument is stated explicitly for performance reasons
                #   -o argument is stated explicitly to avoid ambuigity when running the script
                #   raw_data file and -n argument are mandatory
                # Remaining parameters are stated for clarity and to avoid possible ambiguity
                cmd = ['julia', "scsort.jl", raw_data_file, '-n', n_threads, '-l', '-i', '-o', output_dir, 
                       '-s', start_point, '-e', end_point, '-c', str(params.main.ch_start), '-w', str(params.main.ch_window_width),
                       '-t', start_time_s, '-d', t_duration_s]
                print(cmd)

                try:
                    print("Starting SpikeClassifier sorting process in new terminal...")
                    if os.name == 'nt':  # Windows
                        cmd_str = ' '.join(cmd)
                        process = subprocess.Popen(
                            ['start', 'cmd', '/k', cmd_str],
                            shell=True,
                            cwd=script_dir
                        )
                    else:  # Linux/MacOS
                        cmd_str = ' '.join(cmd)
                        process = subprocess.Popen(
                            ['gnome-terminal', '--', 'bash', '-c', f'{cmd_str}; exec bash'],
                            cwd=script_dir,
                            start_new_session=True
                        )
                    print("Process started in new terminal. Closing UI...")
                    sys.exit()
                except Exception as e:
                    print(f"An error occurred: {e}")
                    sys.exit(1)
