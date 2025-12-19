import flickrapi
from exif import Image
import os, re
from flickr.image_random import read_file_names_from_folder_recursively, get_folders_from_path
import time
from common.my_threading.my_threading import ThreadPooler, execute_in_parallel
import math
import logging
from flickr.token import FlickrToken
from apicommon.base.lib.URLLibRequest import URLLibRequest
from apicommon.base.lib.URLLibResponse import URLLibResponse
import xml.etree.ElementTree as ET
from oauthlib.oauth1 import Client
from urllib.parse import urlencode
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib3 import encode_multipart_formdata
import threading
import urllib3
import shutil
import mimetypes
from pathlib import Path
# Suppress warning logs from the exif/plum modules
logging.getLogger("exif").setLevel(logging.ERROR)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
COUNTER_LOCK = threading.Lock()


# flickr.authenticate_via_browser(perms="write")


def extract_photoid(xml_bytes: bytes) -> str:
    # 1) Decode bytes to text (assuming UTF-8)
    xml_text = xml_bytes.decode("utf-8")

    # 2) Parse into an ElementTree
    root = ET.fromstring(xml_text)

    # 3) Find the <photoid> element and return its text
    photoid_elem = root.find("photoid")
    if photoid_elem is None:
        raise ValueError("No <photoid> element found:" + xml_text)
    return photoid_elem.text


def minus(a: list, b: list) -> list:
    return [item for item in a if item not in b]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def devide_array(array: list, slot_number: int, extra_params) -> list[dict]:
    total_length = len(array)
    params = []
    part_size = math.ceil(total_length / slot_number)

    chunked = list(chunks(array, part_size))

    if part_size == 0:
        part_size = 1
    for i in chunked:
        params.append({"files": i, **extra_params})
    return params


class MyExif:
    def __init__(self, image_path: str, file_obj=None):
        self.image_path = image_path
        self.file_obj = file_obj
        self.data: dict = {}

        if "MP4" not in image_path.upper() and "MOV" not in image_path.upper():
            self.data: dict = self.get_exif()

    def get_exif(self):
        try:
            exif = None
            if not self.file_obj:
                with open(self.image_path, "rb") as image_file:
                    exif = Image(image_file)
            else:
                exif = Image(self.file_obj)

            return exif.get_all()
        except Exception as e:
            return None

    def get_exifs_by_keys(self, keys: list[str]) -> list[str]:
        if not self.data:
            return []
        values = []
        for key in keys:
            try:
                value = self.data.get(key, "")
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="ignore")
                if value:
                    values.append(str(value))
            except Exception as e:
                print(f"[EXIF WARNING] Key '{key}' hiba: {e}")
        return values


class Pagination(object):
    def __init__(self, data: dict = {}):
        self.page = int(data.get("page", None))
        self.pages = data.get("pages", None)
        self.per_page = data.get("perpage", None)
        self.total = data.get("total", None)


class PhotoSet(object):
    def __init__(self, data: dict = {}):
        self.id = data.get("id", None)
        self.owner = data.get("owner", None)
        self.username = data.get("username", None)
        self.primary = data.get("primary", None)
        self.secret = data.get("secret", None)
        self.server = data.get("server", None)
        self.count_views = data.get("count_views", None)
        self.count_photos = data.get("count_photos", None)
        self.count_videos = data.get("count_videos", None)
        self.title = data.get("title", {}).get("_content", None)
        self.description = data.get("description", {}).get("_content", None)


class Photo(object):
    def __init__(self, data: dict = {}):
        self.id = data.get("id", None)
        self.owner = data.get("owner", None)
        self.secret = data.get("secret", None)
        self.server = data.get("server", None)
        self.farm = data.get("farm", None)
        self.title = data.get("title", None)
        self.ispublic = data.get("ispublic", None)
        self.isfriend = data.get("isfriend", None)
        self.isfamily = data.get("isfamily", None)

        self.url = f"https://live.staticflickr.com/{self.server}/{self.id}_{self.secret}.jpg"
        self.url_small = f"https://live.staticflickr.com/{self.server}/{self.id}_{self.secret}_m.jpg"
        self.url_large = f"https://live.staticflickr.com/{self.server}/{self.id}_{self.secret}_b.jpg"
        self.url_original = f"https://live.staticflickr.com/{self.server}/{self.id}_{self.secret}_o.jpg"


class Perm(object):
    def __init__(self, data: dict = {}):
        self.is_public = data.get("ispublic", 0)
        self.is_friend = data.get("isfriend", 0)
        self.is_family = data.get("isfamily", 0)
        self.perm_comment = data.get("permcomment", 0)
        self.perm_addmeta = data.get("permaddmeta", 0)

    def __call__(self, *args, **kwds):
        return self.__dict__


class Myflickr:
    _flickr_api: flickrapi.FlickrAPI = None
    api_key: str = None
    api_secret: str = None

    def __init__(self, api_key=None, api_secret=None, singleton: bool = True):
        Myflickr.api_key = api_key if api_key else Myflickr.api_key
        Myflickr.api_secret = api_secret if api_secret else Myflickr.api_secret
        self.singleton = singleton
        if singleton and Myflickr._flickr_api is not None:
            return
        if singleton and Myflickr._flickr_api is None:
            Myflickr._flickr_api = flickrapi.FlickrAPI(api_key, api_secret, format="parsed-json")
            return
        if not singleton:
            self.flickr_api = flickrapi.FlickrAPI(api_key, api_secret, format="parsed-json")

    @property
    def flickr_api(self):
        if self.singleton:
            return Myflickr._flickr_api
        return self.flickr_api


# flickr.photosets.getList
# flickr.photosets.addPhoto
# flickr.photosets.getPhotos
# flickr.photosets.create
# flickr.photosets.getInfo
# flickr.photos.setPerms
# flickr.photos.getPerms
# flickr.photos.removeTag
# flickr.photos.addTags
# flickr.photos.setTags


class flickr(Myflickr):
    def __init__(self, api_key=None, api_secret=None, singleton: bool = True):
        self.flickr_token = FlickrToken(
            api_key=api_key, api_secret=api_secret, oauth_token=os.environ.get("OAUTH_TOKEN"), oauth_token_secret=os.environ.get("OAUTH_TOKEN_SECRET")
        )
        super().__init__(api_key=self.flickr_token.api_key, api_secret=self.flickr_token.api_secret, singleton=singleton)
        self.oauth_client = Client(
            client_key=self.flickr_token.api_key,
            client_secret=self.flickr_token.api_secret,
            resource_owner_key=self.flickr_api.flickr_oauth.resource_owner_key,
            resource_owner_secret=self.flickr_api.flickr_oauth.resource_owner_secret,
        )

    def _upload(
        self,
        filename,
        title,
        description,
        is_public=0,
        is_friend=0,
        is_family=0,
        tags="",
        hidden=2,
        format="xmlnode",
        file_obj=None,
        *args,
        **kwargs,
    ):
        UPLOAD_URL = "https://up.flickr.com/services/upload/"

        # 1) Prepare your text parameters
        text_params = {
            "title": title,
            "description": description,
            "is_public": str(is_public),
            "is_friend": str(is_friend),
            "is_family": str(is_family),
            "hidden": str(hidden),
            "content_type": "1",
            "safety_level": "1",
            "tags": tags,
        }
        body_for_signature = urlencode(text_params)
        signed_url, oauth_headers, _ = self.oauth_client.sign(
            UPLOAD_URL,
            http_method="POST",
            body=body_for_signature,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        mime, _ = mimetypes.guess_type(filename)
        """
        m = MultipartEncoder(
            fields={
                **text_params,
                "photo": (os.path.basename(filename), filename, mime),
            }
        )
        """
        with open(filename, "rb") as f:
            fields = {**text_params, "photo": (os.path.basename(filename), f.read(), mime)}
            body, content_type = encode_multipart_formdata(fields)
        
        headers = {
            "Authorization": oauth_headers["Authorization"],
            "Content-Type": content_type,
        }
        #body = m.to_string()
        response: URLLibResponse = URLLibRequest.post(
            url=signed_url,
            data=body,
            headers=headers,
        )
        return extract_photoid(response.data)

    def upload(
        self, filename, file_obj, title, description, is_public=0, is_friend=0, is_family=0, tags="", hidden=2, format="xmlnode"
    ) -> Photo:
        start_time = time.time()
        photo_id = self._upload(
            filename=filename,
            title=title,
            description=description,
            is_public=is_public,
            is_friend=is_friend,
            is_family=is_family,
            tags=tags,
            hidden=hidden,
            format=format,
            verify=False,
        )
        photo = Photo(
            {
                "id": photo_id,
                "title": title,
                "description": description,
                "ispublic": is_public,
                "isfriend": is_friend,
                "isfamily": is_family,
                "tags": tags.split(",") if tags else [],
            }
        )
        end_time = time.time()
        print(f"Uploaded photo by {threading.current_thread().name}: {title} with ID: {photo.id} in {end_time - start_time:.2f} seconds")
        return photo

    class photosets:

        class create:
            def __init__(self, title, description, primary_photo_id):
                self.flickr_api = Myflickr().flickr_api
                self.title = title
                self.description = description
                self.primary_photo_id = primary_photo_id

            def call(self):
                result = self.flickr_api.photosets.create(
                    title=self.title, description=self.description, primary_photo_id=self.primary_photo_id
                )
                photoset = PhotoSet(result.get("photoset", {}))
                photoset.title = self.title
                photoset.description = self.description
                print(f"Created photoset: {photoset.title} with ID: {photoset.id}")
                return photoset

        class addPhoto:
            def __init__(self, photoset: PhotoSet, photo: Photo):
                self.flickr_api = Myflickr().flickr_api
                self.photoset = photoset
                self.photo = photo

            def call(self):

                try:
                    result = self.flickr_api.photosets.addPhoto(photoset_id=self.photoset.id, photo_id=self.photo.id)
                    if result.get("stat") == "ok":
                        print(f"Added photo by {threading.current_thread().name} {self.photo.title} to photoset {self.photoset.title}")
                        return True
                    return False
                except flickrapi.exceptions.FlickrError as e:
                    return False

        class getList:
            def __init__(self, user_id, per_page=500, page=1, limit=9999999):
                self.limit = limit
                self.per_page = per_page
                self.page = page
                self.flickr_api = Myflickr().flickr_api
                self.user_id = user_id

            def call(self, photosets: list[PhotoSet] = []):
                result = self.flickr_api.photosets.getList(user_id=self.user_id, page=self.page, per_page=self.per_page)
                pagination = Pagination(result.get("photosets", {}))

                if pagination.page <= pagination.pages and pagination.page <= self.limit:
                    for photoset in result.get("photosets", {}).get("photoset", []):
                        photosets.append(PhotoSet(photoset))

                    flickr.photosets.getList(user_id=self.user_id, per_page=self.per_page, page=self.page + 1, limit=self.limit).call(
                        photosets=photosets
                    )

                return photosets

        class getPhotos:
            def __init__(self, user_id, photoset_id, per_page=500, page=1):
                self.per_page = per_page
                self.page = page
                self.flickr_api = Myflickr().flickr_api
                self.photoset_id = photoset_id
                self.user_id = user_id

            def call(self, photos: list[Photo] = []):
                try:
                    result = self.flickr_api.photosets.getPhotos(
                        user_id=self.user_id, photoset_id=self.photoset_id, page=self.page, per_page=self.per_page
                    )
                except flickrapi.exceptions.FlickrError as e:
                    return []
                pagination = Pagination(result.get("photoset", {}))
                if pagination.page <= pagination.pages:
                    for photo in result.get("photoset", {}).get("photo", []):
                        photos.append(Photo(photo))

                    flickr.photosets.getPhotos(
                        photoset_id=self.photoset_id, per_page=self.per_page, page=self.page + 1, user_id=self.user_id
                    ).call(photos=photos)

                return photos

    class photos:
        class getPerms:
            def __init__(self, photo_id):
                self.flickr_api = Myflickr().flickr_api
                self.photo_id = photo_id

            def call(self):
                result = self.flickr_api.photos.getPerms(photo_id=self.photo_id)
                if result.get("stat") == "ok":
                    return Perm(result.get("perms", {}))
                return None

        class getInfo:
            def __init__(self, photo_id):
                self.flickr_api = Myflickr().flickr_api
                self.photo_id = photo_id

            def call(self):
                return self.flickr_api.photos.getInfo(photo_id=self.photo_id)

        class search:
            def __init__(self, user_id, per_page):
                self.flickr_api = Myflickr().flickr_api
                self.user_id = user_id
                self.per_page = per_page

            def call(self):
                result = self.flickr_api.photos.search(user_id=self.user_id, per_page=self.per_page)
                photos = []
                if result.get("stat") == "ok":
                    for photo in result.get("photos", {}).get("photo", []):
                        photos.append(Photo(photo))
                return photos

        class setTags:
            def __init__(self, photo_id, tags: list[str] = []):
                self.flickr_api = Myflickr().flickr_api
                self.photo_id = photo_id
                self.tags = ",".join(tags)

            def call(self):
                result = self.flickr_api.photos.setTags(photo_id=self.photo_id, tags=self.tags)
                if result.get("stat") == "ok":
                    return True
                return False

        class setPerms:
            def __init__(self, photo_id, perm: Perm = None):
                self.flickr_api = Myflickr().flickr_api
                self.perm: Perm = perm
                self.photo_id = photo_id

            def call(self):
                perms = self.perm() if self.perm else {}
                result = self.flickr_api.photos.setPerms(**perms, photo_id=self.photo_id)
                if result.get("stat") == "ok":
                    return True
                return False


class FlickrSync:
    def __init__(
        self,
        api_key=None,
        api_secret=None,
        number_of_sets=10,
        read_photos: bool = False,
        page: int = 1,
        limit: int = 9999999,
        singleton: bool = True,
    ):
        self.flickr = flickr(api_key=api_key, api_secret=api_secret, singleton=singleton)
        self.photosets = self.flickr.photosets.getList(user_id="138370151@N02", per_page=number_of_sets, page=page, limit=limit).call()
        print(f"Found {len(self.photosets)} photosets in Flickr.")

        if read_photos:
            self.all_photos = self.get_all_photos_from_photoset()
            self.all_photos_title_by_set = self.get_all_title_from_photos_by_set()
            self.all_photos_title = self.get_all_title_from_photos()

    def get_photoset_by_title(self, title: str) -> PhotoSet | None:
        for photoset in self.photosets:
            if photoset.title == title:
                return photoset
        return None

    def get_photosets_by_titles(self, titles: list[str], photo: Photo = None) -> list[PhotoSet]:
        COUNTER_LOCK.acquire()
        photosets: list[PhotoSet] = []
        for title in titles:
            photoset = self.get_photoset_by_title(title)
            if photoset:
                photosets.append(photoset)
            else:
                new_photoset = self.flickr.photosets.create(title=title, description=title, primary_photo_id=photo.id).call()
                photosets.append(new_photoset)
                self.photosets.append(new_photoset)
                print(f"Created new photoset: {new_photoset.title}")
        COUNTER_LOCK.release()
        return photosets

    def copy_failed_media_to_folder(self, file: "FilesInSet") -> None:
        folder = os.path.join(os.path.dirname(file.full_path), "FAILED")
        if not os.path.exists(folder):
            os.makedirs(folder)
        shutil.copyfile(src=file.full_path, dst=os.path.join(folder, file.filename))

    def upload_photo(self, file: "FilesInSet", cnt: int = 3) -> Photo:
        if cnt <= 0:
            print(f"Failed to upload {file.filename_without_ext} after multiple attempts.")
            self.copy_failed_media_to_folder(file)
            return None

        my_exif = MyExif(file_obj=file.file_obj, image_path=file.full_path)
        tags = ",".join(my_exif.get_exifs_by_keys(["model", "lens_model", "focal_length"]) + ["script_upload"])
        try:
            photo: Photo = self.flickr.upload(
                filename=file.full_path,
                file_obj=None,
                title=file.filename_without_ext,
                description=file.filename_without_ext,
                is_public=0,
                is_friend=0,
                is_family=0,
                tags=tags,
            )
        except Exception as e:
            time.sleep(10)
            return self.upload_photo(file=file, cnt=cnt - 1)

        photosets: list[PhotoSet] = self.get_photosets_by_titles(titles=file.sets + ["__2025__"], photo=photo)

        for photoset in photosets:
            self.flickr.photosets.addPhoto(photoset=photoset, photo=photo).call()
        return photo

    def upload_photos_parallel(self, files: list["FilesInSet"], cnt: int = 4) -> list[Photo]:
        def upload_parallel(self: "FlickrSync", files: list = [FilesInSet]):
            for file in files:
                self.upload_photo(file=file)

        params = devide_array(array=files, slot_number=cnt, extra_params={"self": self})

        tp = ThreadPooler(task=upload_parallel, params=params)

        execute_in_parallel(tasks=[tp])

    def get_all_photos_from_photoset(self):
        photos: dict[str, list[Photo]] = {}
        for photoset in self.photosets:
            photos[photoset.title] = self.flickr.photosets.getPhotos(user_id="138370151@N02", per_page=500, photoset_id=photoset.id).call(
                photos=[]
            )
            print(f"Photoset: {photoset.title} - {len(photos[photoset.title])} photos")
        return photos

    def get_all_title_from_photos(self):
        photos: list[str] = []
        for photoset_title in self.all_photos.keys():
            for photo in self.all_photos[photoset_title]:
                photos.append(photo.title)
        return photos

    def get_all_title_from_photos_by_set(self):
        photos: dict[str, list[str]] = {}
        for photoset_title in self.all_photos.keys():
            photos[photoset_title] = []
            for photo in self.all_photos[photoset_title]:
                photos[photoset_title].append(photo.title)
        return photos


class FilesInSet:
    def __init__(self, full_path: str = ""):
        path = Path(full_path) if full_path else None
        self.full_path = full_path
        self.sets = list(path.parts[-3:-1]) if full_path else ""
        self.filename = path.name if full_path else ""
        self.filename_without_ext = path.stem if full_path else ""
        self.is_valid: bool = True if self.filename_without_ext else False
        self.file_obj = None


class FolderToSync:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.files = read_file_names_from_folder_recursively(
            folder_path=self.folder_path, file_extension_list=[".jpg", ".mp4", ".JPG", ".MP4"]
        )
        self.files = [FilesInSet(full_path=i) for i in self.files]
        self.files = list(filter(lambda x: x.is_valid, self.files))
        self.file_names: dict[str, FilesInSet] = {i.filename_without_ext: i for i in self.files}

    def add_file(self, file: FilesInSet):
        self.files.append(file)

    def get_full_path_by_filename_list(self, filename_list: list[str]) -> list[str]:
        return [file.full_path for file in self.files if file.filename_without_ext in filename_list]


if __name__ == "__main__":
    import os
    API_KEY = os.getenv("FLICKR_API_KEY", "")
    API_SECRET = os.getenv("FLICKR_API_SECRET", "")
    fs = FlickrSync(api_key=API_KEY, api_secret=API_SECRET, number_of_sets=500, read_photos=True, limit=1)
    folders: list = [
        "y:\\2019\\",
        "y:\\2020\\",
        "y:\\2021\\",
        "y:\\2022\\",
        "y:\\2023\\",
        "y:\\2024\\",
        "y:\\2025\\",
    ]
    files_by_folder: dict[str, FolderToSync] = {}
    for folder in folders:
        files_by_folder.update({folder: FolderToSync(folder_path=folder)})

    files: FolderToSync
    files_not_in_flickr: list[str] = []
    for files in files_by_folder.values():
        print(f"Processing folder: {files.folder_path} with {len(files.files)} files")
        for on_disk_key, on_disk_value in files.file_names.items():
            if on_disk_key not in fs.all_photos_title:
                files_not_in_flickr.append(on_disk_value)

    fs.upload_photos_parallel(files=files_not_in_flickr, cnt=6)

    pass

"""



photos: list[Photo] = []
photos = flickr(api_key=api_key, api_secret=api_secret).photos.search(user_id="138370151@N02", per_page="10").call()

photo_info = flickr(api_key=api_key, api_secret=api_secret).photos.getInfo(photo_id=photos[0].id).call()

photo_perms = flickr(api_key=api_key, api_secret=api_secret).photos.getPerms(photo_id=photos[0].id).call()

my_exif = MyExif(os.path.abspath(os.path.join(current_path, "54004178222_44360a4956_o.jpg")))
tags = ",".join(my_exif.get_exifs_by_keys(["model", "lens_model", "focal_length"]))

res = flickr().upload(
    filename=os.path.abspath(os.path.join(current_path, "54004178222_44360a4956_o.jpg")),
    title="Test",
    description="Test",
    is_public=0,
    is_friend=0,
    is_family=0,
    tags=tags,
    hidden=2,
    format="xmlnode",
)

add_tags = (
    flickr(api_key=api_key, api_secret=api_secret)
    .photos.setTags(photo_id=photos[0].id, tags=["script_upload", "FE 85mm F1.8", "ILCE-7M3", "85.0 mm"])
    .call()
)
set_perms = flickr(api_key=api_key, api_secret=api_secret).photos.setPerms(photo_id=photos[0].id, perm=Perm()).call()
photosets = flickr(api_key=api_key, api_secret=api_secret).photosets.getList(user_id="138370151@N02", per_page=500).call()
photos_in_photoset = (
    flickr(api_key=api_key, api_secret=api_secret)
    .photosets.getPhotos(user_id="138370151@N02", per_page=500, photoset_id=photosets[0].id)
    .call()
)

new_photoset = flickr(api_key=api_key, api_secret=api_secret).photosets.create(title="Test", description="Test").call()
new_photoset = (
    flickr(api_key=api_key, api_secret=api_secret).photosets.create(title="Test", description="Test", primary_photo_id=photos[0].id).call()
)

"""
