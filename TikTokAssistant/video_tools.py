"""Optional offline FFmpeg chroma-key export; no heavy video processing during stream."""
from pathlib import Path
import shutil


def bundled_ffmpeg():
    """Find a packaged FFmpeg binary without requiring an end-user install."""
    try:
        import imageio_ffmpeg
        candidate = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if candidate.is_file():
            return str(candidate)
    except (ImportError, RuntimeError, OSError, ValueError):
        pass
    return shutil.which('ffmpeg')

def ffmpeg_command(source,output,similarity=0.18,blend=0.08,color='00FF00'):
    src=Path(source);dst=Path(output)
    if not src.is_file() or src.suffix.lower() not in ('.mp4','.webm','.mov','.mkv'):
        raise ValueError('Input video not found or unsupported')
    if dst.suffix.lower()!='.webm' or src.resolve()==dst.resolve():
        raise ValueError('Output must be another .webm file')
    executable = bundled_ffmpeg()
    if not executable:
        raise FileNotFoundError('FFmpeg binary missing; verify that the release includes imageio-ffmpeg')
    similarity=max(0.01,min(1.0,float(similarity)));blend=max(0,min(1.0,float(blend)))
    if len(color)!=6 or any(c not in '0123456789abcdefABCDEF' for c in color):raise ValueError('Invalid key color')
    return [executable,'-hide_banner','-y','-i',str(src),
            '-vf',f'format=rgba,colorkey=0x{color}:{similarity:.3f}:{blend:.3f},format=yuva420p',
            '-c:v','libvpx-vp9','-pix_fmt','yuva420p','-auto-alt-ref','0','-b:v','0','-crf','27',
            '-an',str(dst)]
