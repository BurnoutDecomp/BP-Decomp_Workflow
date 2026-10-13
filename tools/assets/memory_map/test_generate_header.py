"""Keep all allocator descriptor lanes, including unused lanes, faithful to ARTIST."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest

import generate_header


class AllocatorImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path(generate_header.YAML).read_text(encoding="latin1")
        cls.image = generate_header.parse_memory_map_image(cls.text)
        cls.allocators = generate_header.parse_allocators(cls.text)
        cls.originals = json.loads(Path(__file__).with_name(
            "artist_allocator_descriptors.json").read_text(encoding="utf-8"))

    def test_all_descriptor_lanes_match_captured_original_records(self):
        generate_header.validate_memory_map_image(self.image, self.allocators)
        for original in self.originals["records"]:
            with self.subTest(family=original["family"], index=original["index"]):
                raw = bytes.fromhex(original["bytes"])
                self.assertEqual(len(raw), 92)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), original["sha256"])
                descriptor = [list(struct.unpack_from(">II", raw, 52 + lane * 8))
                              for lane in range(5)]
                row = self.image["allocator_events"][original["family"]][original["index"]]
                self.assertEqual(row["descriptor"], descriptor)
                self.assertEqual(row["name"], raw[12:44].split(b"\0", 1)[0].decode("latin1"))
                self.assertEqual([row["bank_id"], row["parent_bank_id"]],
                                 list(struct.unpack_from(">ii", raw, 44)))

    def test_old_zero_size_alignment_loss_is_rejected(self):
        allocators = copy.deepcopy(self.allocators)
        self.assertEqual(allocators["rw_general"][3]["size"][2], 0)
        allocators["rw_general"][3]["align"][2] = 1
        with self.assertRaisesRegex(ValueError, "rw_general descriptor diverges"):
            generate_header.validate_memory_map_image(self.image, allocators)

    def test_nonzero_lane_size_drift_is_rejected(self):
        allocators = copy.deepcopy(self.allocators)
        allocators["rw_linear"][1]["size"][2] -= 16
        with self.assertRaisesRegex(ValueError, "rw_linear descriptor diverges"):
            generate_header.validate_memory_map_image(self.image, allocators)

    def test_missing_original_lane_is_rejected(self):
        image = copy.deepcopy(self.image)
        image["allocator_events"]["raw_resources"][0]["descriptor"].pop()
        with self.assertRaisesRegex(ValueError, "all five X360"):
            generate_header.validate_memory_map_image(image, self.allocators)


if __name__ == "__main__":
    unittest.main()
