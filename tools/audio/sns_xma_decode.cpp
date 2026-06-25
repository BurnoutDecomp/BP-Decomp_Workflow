// Offline decoder for the EA blocked XMA streams used by the boot movies.
//
// Build this against the Xenia FFmpeg fork. That fork exposes the xmaframes
// decoder used by Xenia itself, which accepts one already-extracted XMA frame.
//
// Configure the fork with at least:
//   --disable-x86asm --disable-inline-asm --enable-decoder=xmaframes
//
//   g++ -std=c++17 -O2 sns_xma_decode.cpp \
//       -I/path/to/xenia-ffmpeg \
//       /path/to/xenia-ffmpeg/libavcodec/libavcodec.a \
//       /path/to/xenia-ffmpeg/libavutil/libavutil.a \
//       -pthread -lm -o sns_xma_decode
//
// Usage:
//   sns_xma_decode input.SNS output.wav exact_sample_count

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/error.h>
#include <libavutil/frame.h>
}

namespace {

constexpr std::size_t kPacketBytes = 2048;
constexpr std::size_t kPacketBits = kPacketBytes * 8;
constexpr std::size_t kPacketHeaderBits = 32;
constexpr int kSampleRate = 48000;

std::uint32_t ReadBe24(const std::uint8_t* p) {
  return (static_cast<std::uint32_t>(p[0]) << 16) |
         (static_cast<std::uint32_t>(p[1]) << 8) |
         static_cast<std::uint32_t>(p[2]);
}

std::uint32_t ReadBe32(const std::uint8_t* p) {
  return (static_cast<std::uint32_t>(p[0]) << 24) |
         (static_cast<std::uint32_t>(p[1]) << 16) |
         (static_cast<std::uint32_t>(p[2]) << 8) |
         static_cast<std::uint32_t>(p[3]);
}

void WriteLe16(std::ofstream& out, std::uint16_t value) {
  const std::uint8_t bytes[2] = {
      static_cast<std::uint8_t>(value),
      static_cast<std::uint8_t>(value >> 8),
  };
  out.write(reinterpret_cast<const char*>(bytes), sizeof(bytes));
}

void WriteLe32(std::ofstream& out, std::uint32_t value) {
  const std::uint8_t bytes[4] = {
      static_cast<std::uint8_t>(value),
      static_cast<std::uint8_t>(value >> 8),
      static_cast<std::uint8_t>(value >> 16),
      static_cast<std::uint8_t>(value >> 24),
  };
  out.write(reinterpret_cast<const char*>(bytes), sizeof(bytes));
}

std::vector<std::uint8_t> ReadFile(const char* path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error(std::string("cannot open input: ") + path);
  }
  in.seekg(0, std::ios::end);
  const auto size = in.tellg();
  in.seekg(0, std::ios::beg);
  std::vector<std::uint8_t> data(static_cast<std::size_t>(size));
  if (!data.empty()) {
    in.read(reinterpret_cast<char*>(data.data()), data.size());
  }
  if (!in) {
    throw std::runtime_error("failed reading input");
  }
  return data;
}

// Equivalent to ea_multi_xma for the single-stream SNS variant:
// [EA block header][samples][substream size*4][XMA packet bytes].
std::vector<std::uint8_t> RestorePackets(
    const std::vector<std::uint8_t>& sns) {
  std::vector<std::uint8_t> packets;
  std::size_t offset = 0;

  while (offset < sns.size()) {
    if (sns.size() - offset < 12) {
      throw std::runtime_error("truncated EA block header");
    }

    const std::uint8_t flags = sns[offset];
    const std::uint32_t block_size = ReadBe24(&sns[offset + 1]);
    if (block_size < 12 || block_size > sns.size() - offset) {
      throw std::runtime_error("invalid EA block size");
    }

    const std::uint32_t pseudo_size = ReadBe32(&sns[offset + 8]);
    const std::size_t subblock_size = pseudo_size / 4;
    if (subblock_size < 4 || subblock_size > block_size - 8) {
      throw std::runtime_error("invalid EA XMA subblock size");
    }

    const std::size_t data_size = subblock_size - 4;
    const std::uint8_t* source = &sns[offset + 12];
    packets.insert(packets.end(), source, source + data_size);
    const std::size_t padded =
        (data_size + kPacketBytes - 1) / kPacketBytes * kPacketBytes;
    packets.insert(packets.end(), padded - data_size, 0xFF);

    offset += block_size;
    if ((flags & 0x80) != 0) {
      break;
    }
  }

  if (packets.empty() || packets.size() % kPacketBytes != 0) {
    throw std::runtime_error("restored XMA data is not packet aligned");
  }
  return packets;
}

std::uint32_t ReadBits(const std::uint8_t* data, std::size_t bit_offset,
                       unsigned bit_count) {
  std::uint32_t value = 0;
  for (unsigned i = 0; i < bit_count; ++i) {
    value = (value << 1) |
            ((data[(bit_offset + i) / 8] >>
              (7 - ((bit_offset + i) & 7))) &
             1);
  }
  return value;
}

void AppendBits(std::vector<std::uint8_t>& destination,
                const std::uint8_t* source, std::size_t source_bit,
                std::size_t bit_count) {
  destination.reserve(destination.size() + bit_count);
  for (std::size_t i = 0; i < bit_count; ++i) {
    destination.push_back(static_cast<std::uint8_t>(
        (source[(source_bit + i) / 8] >>
         (7 - ((source_bit + i) & 7))) &
        1));
  }
}

struct FrameBits {
  std::vector<std::uint8_t> bits;
};

std::vector<FrameBits> ExtractFrames(
    const std::vector<std::uint8_t>& packets) {
  std::vector<FrameBits> frames;
  std::vector<std::uint8_t> partial;
  std::size_t expected_partial_bits = 0;

  for (std::size_t packet_offset = 0; packet_offset < packets.size();
       packet_offset += kPacketBytes) {
    const std::uint8_t* packet = &packets[packet_offset];

    // EA's stream uses XMA1 packet headers:
    // sequence:4, metadata:2, continuation bits:15, packet skip:11.
    const std::size_t continuation_bits = ReadBits(packet, 6, 15);
    const std::uint32_t packet_skip = ReadBits(packet, 21, 11);
    if (packet_skip != 0) {
      throw std::runtime_error("unsupported XMA packet header");
    }

    std::size_t bit_offset = kPacketHeaderBits;
    if (!partial.empty()) {
      // 0x4000 is the XMA1 marker for a packet containing only a frame
      // continuation. Since the 32-bit packet header consumes part of that
      // nominal amount, copy the complete payload and continue in the next
      // packet.
      const std::size_t available = kPacketBits - bit_offset;
      const bool continuation_only = continuation_bits >= available;
      std::size_t copied = std::min(continuation_bits, available);
      if (expected_partial_bits != 0) {
        copied =
            std::min(copied, expected_partial_bits - partial.size());
      }
      AppendBits(partial, packet, bit_offset, copied);
      bit_offset += copied;
      if (expected_partial_bits == 0 && partial.size() >= 15) {
        expected_partial_bits = 0;
        for (unsigned i = 0; i < 15; ++i) {
          expected_partial_bits =
              (expected_partial_bits << 1) | partial[i];
        }
      }
      if (expected_partial_bits == 0 ||
          partial.size() > expected_partial_bits) {
        throw std::runtime_error(
            "split XMA frame length mismatch at packet " +
            std::to_string(packet_offset / kPacketBytes) + " (" +
            std::to_string(partial.size()) + " of " +
            std::to_string(expected_partial_bits) + " bits, header says " +
            std::to_string(continuation_bits) + ")");
      }
      if (partial.size() < expected_partial_bits) {
        continue;
      }
      frames.push_back({std::move(partial)});
      partial.clear();
      expected_partial_bits = 0;
      if (continuation_only) {
        continue;
      }
    } else if (continuation_bits != 0) {
      throw std::runtime_error("orphan XMA frame continuation");
    }

    while (bit_offset + 15 <= kPacketBits) {
      const std::uint32_t frame_bits = ReadBits(packet, bit_offset, 15);
      if (frame_bits == 0 || frame_bits == 0x7FFF) {
        break;
      }

      const std::size_t remaining = kPacketBits - bit_offset;
      if (frame_bits > remaining) {
        AppendBits(partial, packet, bit_offset, remaining);
        expected_partial_bits = frame_bits;
        break;
      }

      FrameBits frame;
      AppendBits(frame.bits, packet, bit_offset, frame_bits);
      const bool more_frames = frame.bits.back() != 0;
      frames.push_back(std::move(frame));
      bit_offset += frame_bits;
      if (!more_frames) {
        break;
      }
    }
  }

  if (!partial.empty()) {
    throw std::runtime_error("truncated final XMA frame");
  }
  return frames;
}

std::string AvError(int error) {
  char buffer[AV_ERROR_MAX_STRING_SIZE] = {};
  av_strerror(error, buffer, sizeof(buffer));
  return buffer;
}

std::vector<std::int16_t> DecodeFrames(
    const std::vector<FrameBits>& frames, std::size_t exact_samples,
    int source_channels) {
  const AVCodec* codec = avcodec_find_decoder(AV_CODEC_ID_XMAFRAMES);
  if (codec == nullptr) {
    throw std::runtime_error(
        "Xenia FFmpeg xmaframes decoder is not available");
  }

  AVCodecContext* context = avcodec_alloc_context3(codec);
  AVFrame* frame = av_frame_alloc();
  AVPacket* packet = av_packet_alloc();
  if (context == nullptr || frame == nullptr || packet == nullptr) {
    throw std::runtime_error("FFmpeg allocation failed");
  }

  context->sample_rate = kSampleRate;
  context->channels = source_channels;
  int result = avcodec_open2(context, codec, nullptr);
  if (result < 0) {
    throw std::runtime_error("avcodec_open2: " + AvError(result));
  }

  std::vector<std::int16_t> pcm;
  pcm.reserve(exact_samples * 2);
  std::size_t failed_frames = 0;

  for (const FrameBits& source : frames) {
    const std::size_t frame_bytes = (source.bits.size() + 7) / 8;
    const std::uint8_t padding_end =
        static_cast<std::uint8_t>(frame_bytes * 8 - source.bits.size());
    std::vector<std::uint8_t> encoded(1 + frame_bytes, 0);
    encoded[0] = static_cast<std::uint8_t>(padding_end << 2);
    for (std::size_t i = 0; i < source.bits.size(); ++i) {
      encoded[1 + i / 8] |=
          static_cast<std::uint8_t>(source.bits[i] << (7 - (i & 7)));
    }

    av_packet_unref(packet);
    result = av_new_packet(packet, static_cast<int>(encoded.size()));
    if (result < 0) {
      throw std::runtime_error("av_new_packet: " + AvError(result));
    }
    std::memcpy(packet->data, encoded.data(), encoded.size());

    result = avcodec_send_packet(context, packet);
    if (result < 0) {
      ++failed_frames;
      continue;
    }
    result = avcodec_receive_frame(context, frame);
    if (result < 0) {
      ++failed_frames;
      continue;
    }
    if (context->sample_fmt != AV_SAMPLE_FMT_FLTP || frame->data[0] == nullptr ||
        (source_channels == 2 && frame->data[1] == nullptr)) {
      throw std::runtime_error("unexpected XMA decoder sample format");
    }

    const float* left = reinterpret_cast<const float*>(frame->data[0]);
    const float* right = source_channels == 2
                             ? reinterpret_cast<const float*>(frame->data[1])
                             : left;
    for (int i = 0; i < frame->nb_samples; ++i) {
      const auto convert = [](float sample) {
        return static_cast<std::int16_t>(std::clamp(
          std::lrintf(sample * 32767.0f),
          -32767L,
          static_cast<long>(std::numeric_limits<std::int16_t>::max())));
      };
      pcm.push_back(convert(left[i]));
      pcm.push_back(convert(right[i]));
    }
    av_frame_unref(frame);
  }

  av_packet_free(&packet);
  av_frame_free(&frame);
  avcodec_free_context(&context);

  std::fprintf(stderr, "decoded frames: %zu, rejected frames: %zu\n",
               frames.size() - failed_frames, failed_frames);
  if (failed_frames != 0) {
    throw std::runtime_error("one or more XMA frames failed to decode");
  }
  const std::size_t wanted_values = exact_samples * 2;
  if (pcm.size() < wanted_values) {
    // EA's external stream duration includes the quiet tail after the coded
    // XMA frames. Preserve that presentation duration for movie sync.
    pcm.resize(wanted_values, 0);
  } else {
    pcm.resize(wanted_values);
  }
  return pcm;
}

void WriteWav(const char* path, const std::vector<std::int16_t>& pcm) {
  std::ofstream out(path, std::ios::binary);
  if (!out) {
    throw std::runtime_error(std::string("cannot open output: ") + path);
  }

  const std::uint32_t data_bytes =
      static_cast<std::uint32_t>(pcm.size() * sizeof(std::int16_t));
  out.write("RIFF", 4);
  WriteLe32(out, 36 + data_bytes);
  out.write("WAVEfmt ", 8);
  WriteLe32(out, 16);
  WriteLe16(out, 1);
  WriteLe16(out, 2);
  WriteLe32(out, kSampleRate);
  WriteLe32(out, kSampleRate * 2 * sizeof(std::int16_t));
  WriteLe16(out, 2 * sizeof(std::int16_t));
  WriteLe16(out, 16);
  out.write("data", 4);
  WriteLe32(out, data_bytes);
  out.write(reinterpret_cast<const char*>(pcm.data()), data_bytes);
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 4 && argc != 5) {
    std::fprintf(stderr,
                 "usage: %s input.SNS output.wav exact_sample_count "
                 "[source_channels]\n",
                 argv[0]);
    return EXIT_FAILURE;
  }

  try {
    const unsigned long long parsed = std::strtoull(argv[3], nullptr, 10);
    if (parsed == 0 ||
        parsed > std::numeric_limits<std::uint32_t>::max()) {
      throw std::runtime_error("invalid sample count");
    }

    // These two boot streams are logically mono, but their XMA frame syntax is
    // the two-channel mode. The decoded channels are retained as stereo.
    const int source_channels = argc == 5 ? std::atoi(argv[4]) : 2;
    if (source_channels != 1 && source_channels != 2) {
      throw std::runtime_error("source channels must be 1 or 2");
    }

    const auto sns = ReadFile(argv[1]);
    const auto packets = RestorePackets(sns);
    const auto frames = ExtractFrames(packets);
    const auto pcm = DecodeFrames(frames, static_cast<std::size_t>(parsed),
                                  source_channels);
    WriteWav(argv[2], pcm);

    std::printf("decoded %zu XMA frames, wrote %llu samples (%.3f s)\n",
                frames.size(), parsed,
                static_cast<double>(parsed) / kSampleRate);
    return EXIT_SUCCESS;
  } catch (const std::exception& error) {
    std::fprintf(stderr, "sns_xma_decode: %s\n", error.what());
    return EXIT_FAILURE;
  }
}
