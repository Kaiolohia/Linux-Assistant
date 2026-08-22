import os

max_file_size = 10 * 1024 * 1024  # 10 MB


def read_file(filepath):
    """Read a file with a size limit check"""
    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        size = os.path.getsize(filepath)
        if size > max_file_size:
            return {"error": "File too large"}

        with open(filepath, "r", errors="replace") as f:
            content = f.read()

        return {"filepath": filepath, "size": size, "content": content}
    except Exception as e:
        return {"error": str(e)}


def read_dir(dirpath):
    """ls"""
    dirpath = os.path.expanduser(dirpath)
    if not os.path.exists(dirpath):
        return {"error": f"Directory not found: {dirpath}"}

    files = []
    try:
        max_depth = 60
        for root, dirs, filenames in os.walk(dirpath):
            if len(dirs) >= max_depth:
                dirs.clear()
                break
            for filename in filenames:
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, dirpath)
                files.append(rel_path)
    except Exception as e:
        return {"error": str(e)}

    return {"directory": dirpath, "files": sorted(files)}
