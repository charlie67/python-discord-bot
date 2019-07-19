import unittest
import bot.voice.ytdl_impl as YTDLSource
from bot.voice.voice_helpers import Video, PlayTypes


class TestReceive(unittest.TestCase):

    def test_get_video_search(self):
        video: Video = YTDLSource.YTDLSource.get_video("test", "test author").__getitem__(0)
        self.assertEqual(video.author_name, "test author")
        self.assertEqual(video.file, False)
        self.assertEqual(video.youtube, True)
        self.assertEqual(video.filename, None)
        self.assertEqual(video.play_type.value, PlayTypes.QUEUED.value)
        self.assertTrue(video.video_url.startswith("https://www.youtube.com/watch?"))

    def test_get_video_url(self):
        video: Video = YTDLSource.YTDLSource.get_video("https://www.youtube.com/watch?v=Dqp0sMWTwwI", "test author").__getitem__(0)
        self.assertEqual(video.author_name, "test author")
        self.assertEqual(video.file, False)
        self.assertEqual(video.youtube, True)
        self.assertEqual(video.filename, None)
        self.assertEqual(video.video_length, 60)
        self.assertEqual(video.filename, None)
        self.assertEqual(video.video_id, 'Dqp0sMWTwwI')
        self.assertEqual(video.play_type.value, PlayTypes.QUEUED.value)
        self.assertEqual(video.video_url, "https://www.youtube.com/watch?v=Dqp0sMWTwwI")

