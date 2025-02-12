import sys
import subprocess
import os
import gc
import numpy as np
from phy import IPlugin, connect
from phylib.io.sc_params_dialog import ScParamsDialog
from phylib.io.sc_params import ScParams

def _edit_parameters(params:ScParams):
    updated_params, accepted = ScParamsDialog.edit_params(params)
    if accepted:
        return updated_params
    return None

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
            # TODO: Move to edit actions sub menu
            gui.file_actions.separator()
            @gui.file_actions.add()
            def sc_settings():
                params = controller.sc_params
                if updated_params := _edit_parameters(params):
                    for key in updated_params:
                        params[key] = updated_params[key]
            # @gui.file_actions.add()
            # def backup_sc_params():
            #     print("Save toml file to new place / with new name")
            # @gui.file_actions.add()
            # def save_project_to_new_directory():
            #     print("save files to new directory")
            #     print("restart phy in new directory")
            @gui.file_actions.add()
            def run_sc_sort():
                print("Choose menu with selection (new output dir, etc)")
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
