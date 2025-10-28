import random
import os


def get_folders_from_path(folder_path):
    """
    Get all folders from a given folder path.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        list: A list of folder names.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder {folder_path} does not exist.")

    folders = [f.path for f in os.scandir(folder_path) if f.is_dir()]
    print(f"Found {len(folders)} folders in {folder_path}.")
    return folders


def read_file_names_from_folder_recursively(folder_path, file_extension=None, file_extension_list=None):
    """
    Recursively read all file names from a given folder path.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        list: A list of file names.
    """
    file_names = []
    for root, _, files in os.walk(folder_path):
        if file_extension:
            files = list(filter(lambda file: file_extension in file, files))
        elif file_extension_list:
            files = list(filter(lambda file: any(ext in file for ext in file_extension_list), files))

        for file in files:
            file_names.append(os.path.join(root, file))
    print(f"Found {len(file_names)} files with extension {file_extension or file_extension_list} in {folder_path}.")
    return file_names


def get_files_size_in_mb(file_name):
    """
    Get the size of a file in megabytes.

    Args:
        file_name (str): The name of the file.

    Returns:
        float: The size of the file in megabytes.
    """
    return os.path.getsize(file_name) / (1024 * 1024)


def get_random_file_from_list(file_list):
    """
    Get a random file from a list of files.

    Args:
        file_list (list): The list of files.

    Returns:
        str: A random file name.
    """
    return random.choice(file_list)


def copy_files_to_dest_until_mb_limit(file_list, dest_folder, mb_limit):
    """
    Copy files from a list to a destination folder until the size limit is reached.

    Args:
        file_list (list): The list of files.
        dest_folder (str): The destination folder.
        mb_limit (float): The size limit in megabytes.

    Returns:
        None
    """
    total_size = 0
    total_images = 0
    while total_size < mb_limit:
        try:
            file = get_random_file_from_list(file_list=file_list)
            file_size = get_files_size_in_mb(file)
            os.system(f"copy {file} {dest_folder}")
            total_size += file_size
            total_images += 1
            print(f"Copied {file} to {dest_folder}. Current total size: {total_size:.2f} MB")
            print(f"Total number of files copied: {total_images}")
        except Exception as e:
            print(f"Error copying file {file}: {e}")
            continue


if __name__ == "__main__":
    # Example usage
    folders = get_folders_from_path(folder_path="y:\\")
    print(f"Found {len(folders)} folders.")

    # Read files from each year folder
    files_2019 = read_file_names_from_folder_recursively(folder_path="y:\\2019\\", file_extension=".jpg")

    files_2019 = read_file_names_from_folder_recursively(folder_path="y:\\2019\\", file_extension=".jpg")
    files_2020 = read_file_names_from_folder_recursively(folder_path="y:\\2020\\", file_extension=".jpg")
    files_2021 = read_file_names_from_folder_recursively(folder_path="y:\\2021\\", file_extension=".jpg")
    files_2022 = read_file_names_from_folder_recursively(folder_path="y:\\2022\\", file_extension=".jpg")
    files_2023 = read_file_names_from_folder_recursively(folder_path="y:\\2023\\", file_extension=".jpg")
    files_2024 = read_file_names_from_folder_recursively(folder_path="y:\\2024\\", file_extension=".jpg")
    files_2025 = read_file_names_from_folder_recursively(folder_path="y:\\2025\\", file_extension=".jpg")

    files = files_2019 + files_2020 + files_2021 + files_2022 + files_2023 + files_2024 + files_2025

    copy_files_to_dest_until_mb_limit(file_list=files, dest_folder="D:\\", mb_limit=28 * 1024)
