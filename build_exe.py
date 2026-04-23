from pathlib import Path
import shutil
import sys
import time


RUNTIME_ITEMS = ("config.json", "debug_log.txt", "src", "captures")


def backup_runtime_data(dist_dir, backup_dir):
    if not dist_dir.exists():
        return False

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    copied_any = False
    for name in RUNTIME_ITEMS:
        source = dist_dir / name
        if not source.exists():
            continue

        target = backup_dir / name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        copied_any = True
    return copied_any


def restore_runtime_data(dist_dir, backup_dir):
    if not backup_dir.exists():
        return

    for name in RUNTIME_ITEMS:
        source = backup_dir / name
        if not source.exists():
            continue

        target = dist_dir / name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    shutil.rmtree(backup_dir, ignore_errors=True)


def remove_tree(path):
    if not path.exists():
        return

    last_error = None
    for _ in range(5):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.35)

    if last_error:
        raise last_error


def main():
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is not installed.")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    backup_dir = project_root / ".build_runtime_backup"

    runtime_backed_up = False
    if dist_dir.exists():
        try:
            runtime_backed_up = backup_runtime_data(dist_dir, backup_dir)
        except PermissionError:
            print(f"Cannot back up runtime data from {dist_dir}.")
            print("Close any running Zedsu.exe process and run build_exe.py again.")
            sys.exit(1)

    if build_dir.exists():
        remove_tree(build_dir)

    if dist_dir.exists():
        try:
            remove_tree(dist_dir)
        except PermissionError:
            print(f"Cannot clean {dist_dir}.")
            print("Close any running Zedsu.exe process and run build_exe.py again.")
            sys.exit(1)

    # Phase 8: Build PyInstaller arguments
    pyinstaller_args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "Zedsu",
        "--add-data",
        f"{project_root / 'src'}{';' if sys.platform == 'win32' else ':'}{project_root / 'src'}",
        "--hidden-import",
        "PIL._tkinter_finder",
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "cv2.cv2",
        "--hidden-import",
        "mss",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "numpy._core",
        "--hidden-import",
        "numpy._core._multiarray_umath",
    ]

    # Phase 8: Bundle ONNX YOLO model (D-24 → D-29)
    model_source = project_root / "assets" / "models" / "yolo_gpo.onnx"
    if model_source.exists():
        pyinstaller_args.extend([
            "--add-data",
            f"{model_source}{';' if sys.platform == 'win32' else ':'}assets{chr(92) if sys.platform == 'win32' else '/'}models",
        ])
    else:
        print("[build] WARNING: assets/models/yolo_gpo.onnx not found.")
        print("[build] YOLO detection will be disabled until model is trained and placed.")
        print("[build] To enable: collect screenshots, annotate with LabelImg,")
        print("[build] train YOLO11n, export as ONNX (opset=11), place at assets/models/yolo_gpo.onnx")

    pyinstaller_args.append(str(project_root / "main.py"))

    try:
        PyInstaller.__main__.run(pyinstaller_args)
    finally:
        if runtime_backed_up:
            dist_dir.mkdir(parents=True, exist_ok=True)
            restore_runtime_data(dist_dir, backup_dir)

    exe_path = dist_dir / "Zedsu.exe"
    if not exe_path.exists():
        print("")
        print("Build failed: dist/Zedsu.exe was not created.")
        sys.exit(1)

    print("")
    print("Build complete.")
    print(f"Executable: {exe_path}")
    if runtime_backed_up:
        print("Runtime config, logs, assets, and captures were restored after the rebuild.")
    else:
        print("The app will auto-create config.json, debug_log.txt, src/assets, and captures next to the EXE on first launch.")


if __name__ == "__main__":
    main()
