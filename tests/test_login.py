__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

from unittest import TestCase, main
from unittest.mock import Mock, MagicMock

from pynicotine.slskproto import SlskProtoThread
from pynicotine.utils import ApplyTranslation


class SlskProtoTestCase(TestCase):

    def setUp(self) -> None:
        ApplyTranslation()

    def test_instantiate_proto(self) -> None:
        SlskProtoThread(
            ui_callback=Mock(), queue=Mock(), bindip='',
            port=1,  # proto cannot bind to privileged port, the thus thread does not run.
            config=MagicMock(), eventprocessor=Mock()
        )


if __name__ == '__main__':
    main()
