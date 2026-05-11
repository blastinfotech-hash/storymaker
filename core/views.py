from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404


@login_required
def protected_media(request, path):
    file_path = Path(settings.MEDIA_ROOT) / path
    if not file_path.exists() or not file_path.is_file():
        raise Http404("File not found")
    return FileResponse(file_path.open("rb"), as_attachment=False)
