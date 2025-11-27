import subprocess
import time
import os

def generate_cog(input_file, output_file):
   
    output_format = "COG"
    output_format_options = [
        "COMPRESS=LZW",
        "BLOCKSIZE=256",
        "RESAMPLING=NEAREST",
        "OVERVIEW_RESAMPLING=AVERAGE"
    ]
    overviews = [2, 4, 8, 16, 32, 64]

    try:
        # Set GDAL environment options to avoid temporary files
        os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'YES'
        os.environ['CPL_VSIL_CURL_NON_CACHED'] = '/vsimem'
        
        # Construct the gdal_translate command
        translate_command = [
            "gdal_translate",
            "-of", output_format,
        ]
        for option in output_format_options:
            translate_command.extend(["-co", option])
        translate_command.extend([input_file, output_file])
        
        # Record start time
        start_time = time.time()
      
        # Run the gdal_translate command and wait for it to complete
        subprocess.run(translate_command, check=True)

        # Construct the gdaladdo command
        addo_command = ["gdaladdo", "-r", "average", output_file] + [str(level) for level in overviews]

        # Run the gdaladdo command and wait for it to complete
        subprocess.run(addo_command, check=True)

        # Record end time
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"COG generation and overviews creation completed: {output_file}")
        print(f"Time taken: {elapsed_time:.2f} seconds")
    except subprocess.CalledProcessError as e:
        print(f"Error during COG generation or overviews creation: {e}")
    finally:
        # Clean up environment variables
        os.environ.pop('GDAL_DISABLE_READDIR_ON_OPEN', None)
        os.environ.pop('CPL_VSIL_CURL_NON_CACHED', None)

# Example usage
input_file = "/home/coderize/IADSNEW/fgic/media/hot_folder/4_GB_file.tif"
output_file = "/home/coderize/Local_Ingester_Folder/4_GB_file_COG_3.tif"
generate_cog(input_file, output_file)
