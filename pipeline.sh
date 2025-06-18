#!/bin/bash
## @author Luis Kröner
## @version 1.0
## @date   4th June 2025
## @file
## @brief This tool processes a labeled .nii (NIfTI) file and generates a visual model
## in the form of a smoothed triangulated irregular network (TIN).
## @details The user is prompted to enter several parameters. If no input is provided, default
## values are used. The tool handles all necessary input/output and parameter management,
## processing through a pipe of Python scripts.

## @section Dependencies
## - Python3
## - Python packages: SimpleITK, ITK, VTK, Numpy
## - Linux find command if absolute paths are not specified by user
## @section Workflow
## The script performs the following tasks:
## - Accepts input parameters from the user (input .nii file, output folder, filtering/segmentation parameters)
## - Validates and processes input data
## - Runs a series of five Python scripts for conversion, segmentation, filtering,
##   generation of TIN networks, and TIN optimization

echo "CTA MODEL FRAMEWORK: Process a .nii file and generate a visual model (smoothed triangulated irregular network (.vtk))."
echo "Python3 Dependencies: SimpleITK,itk, vtk, numpy. If you specify file and folder names instead of absolute paths, Linux find command must be available"

echo ""
echo ""
echo ""
echo "INFORMATION: This script uses the recursive linux 'find' command to locate the filename within /home/"
echo "INFORMATION: If you wish to specify an absolute file path yourself, press ENTER -> leave 1. empty on the FIRST request"
echo ""
echo "1. **Input .nii File: The NIfTI (.nii) file you want to process**"
echo "**Ensure your file name is unique within the home subdirectory. Otherwise the first occurrence will be processed**"
echo "   - Example: 'ct_1126_label.nii'."
read -p "Enter the input file " input_nii_file

## @var using_absolute_path_input_file
## Flag to differentiate between absolute path and filename input.
using_absolute_path_input_file="0"

if [ -z "$input_nii_file" ]; then
   using_absolute_path_input_file="1"
   echo "**Input absolute file path of .nii File: The NIfTI (.nii) file you want to process."
  read -p "Enter absolute file path " input_nii_file
fi

echo ""
echo "INFORMATION: This script uses the recursive linux 'find' command to locate the folder within /home/"
echo "INFORMATION: If you wish to specify an absolute folder path yourself, press ENTER -> leave 2. empty on the FIRST request"
echo ""
echo "2. **Output Folder for .mha File: folder where the converted .mha file will be saved.**"
echo "Make sure the folder name is unique within the home subdirectory. Otherwise the first occurrence will be selected."
echo "   - Example: 'output_folder'. Pass ONLY the folder name"
read -p "Enter the name of the output folder " mha_folder

## @var using_absolute_path_output_folder
## Flag to differentiate between absolute path and folder name input.
using_absolute_path_output_folder="0"

if [ -z "$mha_folder" ]; then
   using_absolute_path_output_folder="1"
   echo "**Input absolute folder path where the .mha file will be saved "
  read -p "Enter absolute folder path " mha_folder
fi

echo ""
echo "INFORMATION: This script uses the recursive linux 'find' command to locate the folder within /home/"
echo "INFORMATION: If you wish to specify an absolute folder path yourself, press ENTER -> leave 3. empty on the FIRST request"
echo ""
echo "3. **Output folder for the segmented components of the image.**"
echo "Make sure the folder name is unique within the home subdirectory.. Otherwise the first occurrence will be selected. "
echo "   - Example: 'component_folder'. Pass ONLY the folder name"
read -p "Enter the name of the component folder " components_path

## @var using_absolute_path_components_folder
## Flag to differentiate between absolute path and folder name input
using_absolute_path_components_folder="0"

if [ -z "$components_path" ]; then
   using_absolute_path_components_folder="1"
   echo "**Input absolute folder path where the segmented components will be saved."
  read -p "Enter absolute folder path " components_path
fi

echo ""
echo "4. **Lower treshold regarding component size measured in voxel count for the segmented components: Increasing this value removes bigger and bigger labeled segments from the image. **"
echo "   - Example: '50 is default, for very fine structures, set this parameter close to zero'."
read -p "Enter the time step or ENTER for default value " component_size

echo ""
echo "5. **Time Step for Anisotropic Filtering: Increasing this value speeds up diffusion, leading to stronger smoothing but higher risk of instability. **"
echo "   - Example: '0.0025 is default'."
read -p "Enter the time step or ENTER for default value " time_step

echo ""
echo "6. **Conductance Value for Anisotropic Filtering: Increasing this value enhances diffusion across edges, preserving structures while reducing noise. **"
echo "   - Example: '2.0 is default'."
read -p "Enter the conductance value or ENTER for default value " conductance

echo ""
echo "7. **Iteration count for Anisotropic Filtering: Increasing this value applies more diffusion steps, leading to stronger smoothing over time. **"
echo "   - Example: '16 is default'."
read -p "Enter the number of iterations or ENTER for default value " iterations

echo ""
echo "8. **Contour value for generating the TIN net:  Increasing this value extracts higher intensity contours, highlighting more detailed features. **"
echo "   - Example: '0.5 is default'."
read -p "Enter the value or ENTER for default value " contour

echo ""
echo "9. **Cleaning tolerance parameter: Increasing this value merges points within a larger distance, potentially reducing fine geometric detail.**"
echo "   - Example: '0.00025 is default'."
read -p "Enter the value or ENTER for default value " cleaning_tolerance

echo ""
echo "10. **Artifact tolerance for TIN net: Increasing this value allows more artifacts to be removed, reducing detail but improving mesh quality. **"
echo "   - Example: '150 is default'."
read -p "Enter the value or ENTER for default value " artifact_tolerance

echo ""
echo "11. **Target reduction parameter: Increasing this value reduces the polygon count more aggressively, simplifying the geometry further. **"
echo "   - Example: '0.01 is default'."
read -p "Enter the value or ENTER for default value " target_reduction

echo ""
echo "12. **Relaxation factor for Laplacian smoothing of TIN net: Increasing this value enhances smoothing intensity per iteration, leading to a more pronounced surface smoothing effect. **"
echo "   - Example: '0.1 is default'."
read -p "Enter the value or ENTER for default value " relaxation

echo ""
echo "13. **Iteration count for Laplacian smoothing: Increasing this value applies more smoothing passes, leading to smoother surface and reduced detail. **"
echo "   - Example: '40 is default'."
read -p "Enter the value or ENTER for default value " tin_iterations

echo ""
echo "14. **Hole tolerance for Mesh optimization. This parameter is a threshold for hole removal in the mesh. Holes with a radius up to this value are removed from the mesh   **"
echo "   - Example: '10 is default'."
read -p "Enter the value or ENTER for default value " hole_tolerance

## @brief Define and set up the log file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/project.log"
> "$LOG_FILE"

## @brief If no user input is provided, default values are assigned to the variables.
if [[ -z "$time_step" ]]; then
    time_step="0.0025"
fi

if [[ -z "$conductance" ]]; then
    conductance="2.0"
fi

if [[ -z "$iterations" ]]; then
    iterations="16"
fi

if [[ -z "$component_size" ]]; then
    component_size="50"
fi

if [[ -z "$contour" ]]; then
    contour="0.5"
fi

if [[ -z "$cleaning_tolerance" ]]; then
    cleaning_tolerance="0.00025"
fi

if [[ -z "$artifact_tolerance" ]]; then
    artifact_tolerance="150"
fi

if [[ -z "$target_reduction" ]]; then
    target_reduction="0.01"
fi

if [[ -z "$relaxation" ]]; then
    relaxation="0.1"
fi

if [[ -z "$tin_iterations" ]]; then
    tin_iterations="40"
fi

if [[ -z "$hole_tolerance" ]]; then
    hole_tolerance="10"
fi

check_integer() {
    local var_name="$1"
    local var_value="$2"

    if ! [[ "$var_value" =~ ^[0-9]+$ ]]; then
        echo "Error: $var_name '$var_value' must be a valid integer." | tee -a "$LOG_FILE"
        exit 1
    fi
}

check_float() {
    local var_name="$1"
    local var_value="$2"

    if ! [[ "$var_value" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        echo "Error: $var_name '$var_value' must be a valid float." | tee -a "$LOG_FILE"
        exit 1
    fi
}

check_integer "iterations" "$iterations"
check_integer "tin_iterations" "$tin_iterations"
check_integer "component_size" "$component_size"
check_integer "artifact_tolerance" "$artifact_tolerance"
check_integer "hole_tolerance" "$hole_tolerance"
check_float "target_reduction" "$target_reduction"
check_float "time_step" "$time_step"
check_float "conductance" "$conductance"
check_float "contour" "$contour"
check_float "relaxation" "$relaxation"
check_float "cleaning_tolerance" "$cleaning_tolerance"



## @brief Check whether the input file is given as an absolute path or filename within home dir (according to the flag), then verify validity
if [ "$using_absolute_path_input_file" == "0" ]; then
    absolute_nii_file=$(find "$HOME" -type f -name "$input_nii_file" 2>/dev/null | head -n 1)

    if [ -z "$absolute_nii_file" ]; then
        echo "Error: The file '$input_nii_file' does not exist within the home dir." | tee -a "$LOG_FILE"
        exit 1
    elif [[ "$absolute_nii_file" != *.nii ]]; then
        echo "Error: The file '$absolute_nii_file' is not in .nii format." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "File found: $absolute_nii_file" | tee -a "$LOG_FILE"
    fi
else
  absolute_nii_file=$input_nii_file
   if [ ! -f "$absolute_nii_file" ]; then
        echo "Error: The file '$absolute_nii_file' does not exist." | tee -a "$LOG_FILE"
        exit 1
    elif [[ "$absolute_nii_file" != *.nii ]]; then
        echo "Error: The file '$absolute_nii_file' is not in .nii format." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "Absolute file path verified: $absolute_nii_file" | tee -a "$LOG_FILE"
    fi

fi

## @brief Check whether the output folder is given as an absolute path or folder name within home dir (according to the flag), then verify validity
if [ "$using_absolute_path_output_folder" == "0" ]; then
    absolute_mha_folder=$(find "$HOME" -type d -name "$mha_folder" 2>/dev/null | head -n 1)

    if [ -z "$absolute_mha_folder" ]; then
        echo "Error: The folder '$mha_folder' does not exist within the home dir." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "Folder found: $absolute_mha_folder" | tee -a "$LOG_FILE"
    fi
else
    absolute_mha_folder="$mha_folder"

    if [ ! -d "$absolute_mha_folder" ]; then
        echo "Error: The folder '$absolute_mha_folder' does not exist." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "Absolute folder path verified: $absolute_mha_folder" | tee -a "$LOG_FILE"
    fi
fi

## @brief Check whether components folder is given as an absolute path or folder name within home dir (according to the flag), then verify validity
if [ "$using_absolute_path_components_folder" == "0" ]; then
    absolute_components_folder=$(find "$HOME" -type d -name "$components_path" 2>/dev/null | head -n 1)

    if [ -z "$absolute_components_folder" ]; then
        echo "Error: The folder '$components_path' does not exist within the home dir." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "Folder found: $absolute_components_folder" | tee -a "$LOG_FILE"
    fi
else
    absolute_components_folder="$components_path"

    if [ ! -d "$absolute_components_folder" ]; then
        echo "Error: The folder '$absolute_components_folder' does not exist." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "Absolute folder path verified: $absolute_components_folder" | tee -a "$LOG_FILE"
    fi
fi

## @brief Log completion and begin execution
echo "All parameters valid, starting pipe" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

python3 convert.py "$absolute_nii_file" "$absolute_mha_folder" |
python3 segment.py "$absolute_components_folder" "$component_size" |
python3 filter.py "$absolute_components_folder" "$time_step" "$conductance" "$iterations"  |
python3 generate_net.py "$contour" |
python3 optimize_net.py "$cleaning_tolerance" "$relaxation" "$tin_iterations" "$artifact_tolerance" "$target_reduction" "$hole_tolerance"

# ==============================================================================
# End of script
# ==============================================================================
