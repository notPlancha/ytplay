"""Type definitions for YouTube API responses and internal data structures."""

from collections.abc import Mapping
from typing import Literal, NotRequired, Protocol, TypedDict


# YouTube API Response Types
class YouTubeListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[dict[str, object]]


class YouTubeInsertResponse(TypedDict):
  kind: str
  etag: str
  id: str


class PlaylistSnippet(TypedDict):
  title: str
  publishedAt: str
  description: NotRequired[str]


class PlaylistContentDetails(TypedDict):
  itemCount: int


class PlaylistStatus(TypedDict):
  privacyStatus: NotRequired[str]


class Playlist(TypedDict):
  id: str
  snippet: PlaylistSnippet
  contentDetails: PlaylistContentDetails
  status: PlaylistStatus


class VideoResourceId(TypedDict):
  kind: str
  videoId: str


class PlaylistItemSnippet(TypedDict):
  publishedAt: str
  channelId: str
  title: str
  description: NotRequired[str]
  channelTitle: str
  playlistId: str
  position: int
  resourceId: VideoResourceId
  videoOwnerChannelTitle: NotRequired[str]
  videoOwnerChannelId: NotRequired[str]


class PlaylistItem(TypedDict):
  id: str
  snippet: PlaylistItemSnippet


class VideoContentDetails(TypedDict):
  duration: str  # ISO 8601 duration format (e.g., "PT4M13S")
  definition: NotRequired[str]
  caption: NotRequired[str]


class Video(TypedDict):
  id: str
  snippet: PlaylistItemSnippet  # Reusing the snippet structure
  contentDetails: VideoContentDetails


class YouTubePlaylistListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[Playlist]


class YouTubePlaylistItemListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[PlaylistItem]


class YouTubeVideoListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[Video]


# Enhanced video type with duration info for internal use
class EnhancedVideo(TypedDict):
  id: str
  snippet: PlaylistItemSnippet
  video_id: str
  duration: str


# Request objects that can be executed
class YouTubeRequest(Protocol):
  def execute(self) -> dict[str, object]: ...


class YouTubePlaylistRequest(Protocol):
  def execute(self) -> YouTubePlaylistListResponse: ...


class YouTubePlaylistItemRequest(Protocol):
  def execute(self) -> YouTubePlaylistItemListResponse: ...


class YouTubeVideoRequest(Protocol):
  def execute(self) -> YouTubeVideoListResponse: ...


class YouTubeInsertRequest(Protocol):
  def execute(self) -> YouTubeInsertResponse: ...


class YouTubeDeleteRequest(Protocol):
  def execute(self) -> dict[str, object]: ...


class YouTubePlaylistsResource(Protocol):
  def list(
    self,
    *,
    part: str,
    mine: bool | None = None,
    id: str | None = None,
    maxResults: int,
    pageToken: str | None = None,
  ) -> YouTubePlaylistRequest: ...
  def insert(
    self, *, part: str, body: Mapping[str, object]
  ) -> YouTubeInsertRequest: ...
  def delete(self, *, id: str) -> YouTubeDeleteRequest: ...


class YouTubePlaylistItemsResource(Protocol):
  def list(
    self, *, part: str, playlistId: str, maxResults: int, pageToken: str | None = None
  ) -> YouTubePlaylistItemRequest: ...
  def insert(
    self, *, part: str, body: Mapping[str, object]
  ) -> YouTubeInsertRequest: ...


class YouTubeVideosResource(Protocol):
  def list(
    self, *, part: str, id: str, maxResults: int | None = None
  ) -> YouTubeVideoRequest: ...


class YouTubeService(Protocol):
  def playlists(self) -> YouTubePlaylistsResource: ...
  def playlistItems(self) -> YouTubePlaylistItemsResource: ...
  def videos(self) -> YouTubeVideosResource: ...


# Type aliases
SortCriteria = Literal["upload_date", "duration", "title", "channel", "position"]
PrivacyStatus = Literal["private", "public", "unlisted"]
TextOrJson = Literal["text", "json"]
