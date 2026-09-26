"""Shared upload service for locally stored media assets."""

import os
import uuid
from io import BytesIO
from PIL import Image as PILImage

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from django.utils import timezone

from .models import MediaAsset


def media_asset_upload_path(instance, filename):
    """Generate a non-guessable local storage path while retaining the suffix."""
    extension = os.path.splitext(filename)[1].lower()
    created_at = instance.created_at or timezone.now()
    return f'media_assets/{created_at:%Y/%m}/{uuid.uuid4().hex}{extension}'


def generate_image_derivatives(asset):
    """Generate resized image derivatives for thumbnails/web sizes."""
    if not asset.is_renderable_image or not asset.file:
        return

    try:
        img = PILImage.open(asset.file)
        img_format = img.format or 'PNG'
        base_width = 800
        base_height = int(img.height * (base_width / img.width))

        # Large derivative (for page display)
        large_img = img.resize((base_width, base_height), PILImage.LANCZOS)
        large_io = BytesIO()
        large_img.save(large_io, format=img_format)
        large_io.seek(0)
        asset.large_image.save(
            f'large_{uuid.uuid4().hex}.{img_format.lower()}',
            ContentFile(large_io.read()),
            save=False,
        )

        # Medium derivative (for thumbnails)
        med_width = 400
        med_height = int(img.height * (med_width / img.width))
        med_img = img.resize((med_width, med_height), PILImage.LANCZOS)
        med_io = BytesIO()
        med_img.save(med_io, format=img_format)
        med_io.seek(0)
        asset.medium_image.save(
            f'medium_{uuid.uuid4().hex}.{img_format.lower()}',
            ContentFile(med_io.read()),
            save=False,
        )

        # Small derivative (for listing cards)
        sm_width = 200
        sm_height = int(img.height * (sm_width / img.width))
        sm_img = img.resize((sm_width, sm_height), PILImage.LANCZOS)
        sm_io = BytesIO()
        sm_img.save(sm_io, format=img_format)
        sm_io.seek(0)
        asset.small_image.save(
            f'small_{uuid.uuid4().hex}.{img_format.lower()}',
            ContentFile(sm_io.read()),
            save=False,
        )

        asset.status = MediaAsset.STATUS_READY
        asset.save(update_fields=['status', 'large_image', 'medium_image', 'small_image'])

    except Exception as e:
        asset.status = MediaAsset.STATUS_FAILED
        asset.failure_reason = f'Image processing error: {str(e)[:200]}'
        asset.save(update_fields=['status', 'failure_reason'])


def store_uploaded_media(upload, *, owner=None, content_object=None, alt_text='', is_public=False):
    """Validate, persist, and audit one uploaded file.

    Invalid files are retained as failure records without their payload. This
    lets staff explain failed client requests without keeping unsafe content.
    """
    from django.utils import timezone

    # Sanitize filename
    original_name = getattr(upload, 'name', 'unnamed-upload') or 'unnamed-upload'
    safe_name = get_valid_filename(original_name)[:255]
    # Ensure we keep an extension if possible
    name, ext = os.path.splitext(safe_name)
    if ext:
        safe_name = name + ext
    else:
        safe_name = name + '.bin'

    asset = MediaAsset(
        file=upload,
        original_name=safe_name,
        mime_type=getattr(upload, 'content_type', '') or '',
        size_bytes=getattr(upload, 'size', 0) or 0,
        kind=MediaAsset.kind_for_mime_type(getattr(upload, 'content_type', '') or ''),
        owner=owner,
        alt_text=alt_text.strip()[:255] if alt_text else '',
        is_public=is_public,
    )

    if content_object is not None:
        asset.content_object = content_object

    try:
        asset.full_clean()
        asset.status = MediaAsset.STATUS_READY
        asset.save()
        # Generate image derivatives for image files
        if asset.is_renderable_image:
            generate_image_derivatives(asset)
        return asset, True
    except (ValidationError, OSError) as error:
        asset.file = None
        asset.status = MediaAsset.STATUS_FAILED
        asset.failure_reason = '; '.join(getattr(error, 'messages', [str(error)]))[:2000]
        asset.save()
        return asset, False
