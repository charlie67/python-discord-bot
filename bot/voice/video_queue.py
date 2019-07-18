from voice.voice_helpers import Video
import discord


class VideoQueueItem:
    message_context: discord.message
    video: Video
    voice_client: discord.voice_client

    def __init__(self, message_context, video, voice_client) -> None:
        self.voice_client = voice_client
        self.video = video
        self.message_context = message_context


class VideoQueue:
    video_queue_list = []
    total_play_time = 0

    def add_to_queue(self, queue_item_to_add: VideoQueueItem):
        self.video_queue_list.append(queue_item_to_add)
        self.total_play_time += int(queue_item_to_add.video.video_length)

    def get_and_remove_first_item(self) -> VideoQueueItem:
        item_to_return: VideoQueueItem = self.video_queue_list.__getitem__(0)
        self.video_queue_list.__delitem__(0)
        self.total_play_time -= item_to_return.video.video_length
        return item_to_return

    def length(self) -> int:
        return self.video_queue_list.__len__()

    def is_next_song_file(self):
        return self.video_queue_list.__getitem__(0).video.file
