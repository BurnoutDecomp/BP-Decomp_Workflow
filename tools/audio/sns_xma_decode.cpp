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
#include <libavutil/channel_layout.h>
#include <libavutil/error.h>
#include <libavutil/frame.h>
}

namespace {

constexpr std::size_t kPacketBytes = 2048;
constexpr std::size_t kPacketBits = kPacketBytes * 8;
constexpr std::size_t kPacketHeaderBits = 32;
// Default; overridden by the SNR header (e.g. the video logos are 48 kHz but the
// in-game streams are 44.1 kHz). The XMA frame decode is rate-agnostic, but the
// decoder context and the output WAV header must carry the stream's real rate.
int g_sample_rate = 48000;

// EA "GenericRwacWaveContent" stream header (the SNR resource that pairs with a
// streamed .SNS). It carries the authoritative channel count, sample rate, total
// sample count, and -- crucially -- a *prefetched* leading chunk of XMA stored
// inline (the first ~0.3 s of audio, i.e. the attack), with the remainder
// streamed from the .SNS. Layout:
//   [0x00] 16-byte resource wrapper ([u32 payload_size][u32 header_size=0x10]..)
//   [0x10] EAAC header: u32 (version:4 codec:4 channels:6 sample_rate:18),
//                       u32 (type:2 loop:1 num_samples:29)
//   [0x18] extended: u32 prefetch_samples, u32 prefetch_size, ...
//   [0x28] prefetched XMA bytes (prefetch_size of them)
// See burnout.wiki + Xenia xma; codec 3 == EA-XMA.
struct SnrHeader {
  int channels = 0;
  int sample_rate = 0;
  std::uint32_t num_samples = 0;
  std::uint32_t prefetch_samples = 0;
  std::vector<std::uint8_t> prefetch;  // raw embedded XMA bytes (un-padded)
  bool valid = false;
};

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

// Parse the SNR (GenericRwacWaveContent) resource. Returns the authoritative
// channels/sample_rate/num_samples and the inline prefetched XMA bytes.
SnrHeader ParseSnr(const std::vector<std::uint8_t>& d) {
  SnrHeader h;
  constexpr std::size_t kBase = 0x10;       // skip the 16-byte resource wrapper
  constexpr std::size_t kDataOffset = 0x28;  // wrapper + EAAC(8) + extended(16)
  if (d.size() < kDataOffset) {
    throw std::runtime_error("SNR too small / not a GenericRwacWaveContent");
  }
  const std::uint32_t h1 = ReadBe32(&d[kBase]);
  const std::uint32_t h2 = ReadBe32(&d[kBase + 4]);
  const int codec = static_cast<int>((h1 >> 24) & 0xF);
  h.channels = static_cast<int>((h1 >> 18) & 0x3F) + 1;
  h.sample_rate = static_cast<int>(h1 & 0x3FFFF);
  h.num_samples = h2 & 0x1FFFFFFF;
  if (codec != 3) {  // 3 == EA-XMA
    throw std::runtime_error("SNR codec is not EA-XMA (" +
                             std::to_string(codec) + ")");
  }
  h.prefetch_samples = ReadBe32(&d[kBase + 8]);            // 0x18
  const std::uint32_t prefetch_size = ReadBe32(&d[kBase + 12]);  // 0x1c
  const std::size_t available = d.size() - kDataOffset;
  // prefetch_size is occasionally rounded a few bytes long; clamp to what's
  // actually present.
  const std::size_t bytes = std::min<std::size_t>(prefetch_size, available);
  h.prefetch.assign(d.begin() + kDataOffset, d.begin() + kDataOffset + bytes);
  h.valid = true;
  return h;
}

// Pad the inline prefetch XMA to a packet boundary and prepend it to the
// .SNS-restored packets, yielding one continuous XMA packet stream covering the
// whole sound (prefetched attack + streamed body).
std::vector<std::uint8_t> CombinePackets(const SnrHeader& snr,
                                         const std::vector<std::uint8_t>& sns) {
  std::vector<std::uint8_t> combined;
  if (snr.valid && !snr.prefetch.empty()) {
    combined = snr.prefetch;
    const std::size_t padded =
        (combined.size() + kPacketBytes - 1) / kPacketBytes * kPacketBytes;
    combined.resize(padded, 0xFF);
  }
  const std::vector<std::uint8_t> body = RestorePackets(sns);
  combined.insert(combined.end(), body.begin(), body.end());
  return combined;
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

std::size_t ReadFrameLength(const std::vector<std::uint8_t>& bits) {
  std::size_t frame_bits = 0;
  for (unsigned i = 0; i < 15; ++i) {
    frame_bits = (frame_bits << 1) | bits[i];
  }
  return frame_bits;
}

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
      const std::size_t continuation_payload =
          std::min(continuation_bits, available);
      std::size_t copied = 0;

      if (expected_partial_bits == 0 && partial.size() < 15) {
        const std::size_t needed = 15 - partial.size();
        const std::size_t chunk =
            std::min(needed, continuation_payload);
        AppendBits(partial, packet, bit_offset, chunk);
        bit_offset += chunk;
        copied += chunk;

        if (partial.size() == 15) {
          expected_partial_bits = ReadFrameLength(partial);
        }
      }

      if (expected_partial_bits != 0) {
        if (partial.size() > expected_partial_bits) {
          throw std::runtime_error(
              "split XMA frame length mismatch at packet " +
              std::to_string(packet_offset / kPacketBytes));
        }

        const std::size_t needed =
            expected_partial_bits - partial.size();
        const std::size_t chunk =
            std::min(needed, continuation_payload - copied);
        AppendBits(partial, packet, bit_offset, chunk);
        bit_offset += chunk;
        copied += chunk;
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
      if (!continuation_only && copied != continuation_payload) {
        throw std::runtime_error(
            "XMA continuation overran completed frame at packet " +
            std::to_string(packet_offset / kPacketBytes));
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
      if (bit_offset + 15 > kPacketBits) {
        const std::size_t remaining = kPacketBits - bit_offset;
        if (remaining != 0) {
          AppendBits(partial, packet, bit_offset, remaining);
          expected_partial_bits = 0;
        }
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

  context->sample_rate = g_sample_rate;
  // AVCodecContext::channels was removed in the FFmpeg fork's libavcodec major
  // bump; the channel count now travels through ch_layout.
  av_channel_layout_default(&context->ch_layout, source_channels);
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
  // The XMA hardware decoder consumes a priming/partial frame at the stream
  // tail that libavcodec cannot complete on its own; tolerate a couple of
  // trailing rejects rather than discarding an otherwise complete decode.
  if (failed_frames > 2) {
    throw std::runtime_error("too many XMA frames failed to decode");
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
  WriteLe32(out, g_sample_rate);
  WriteLe32(out, g_sample_rate * 2 * sizeof(std::int16_t));
  WriteLe16(out, 2 * sizeof(std::int16_t));
  WriteLe16(out, 16);
  out.write("data", 4);
  WriteLe32(out, data_bytes);
  out.write(reinterpret_cast<const char*>(pcm.data()), data_bytes);
}

}  // namespace

// Detect whether arg looks like a path to an existing SNR file (vs a number).
bool FileExists(const char* path) {
  std::ifstream f(path, std::ios::binary);
  return static_cast<bool>(f);
}

int main(int argc, char** argv) {
  // Preferred:  sns_xma_decode input.SNS output.wav stream.snr
  //   The SNR (GenericRwacWaveContent) supplies channels, sample rate, total
  //   sample count, and the prefetched leading XMA (the attack) that is NOT in
  //   the .SNS -- without it the first ~0.3 s is lost.
  // Legacy:     sns_xma_decode input.SNS output.wav exact_sample_count [channels]
  if (argc != 4 && argc != 5) {
    std::fprintf(stderr,
                 "usage: %s input.SNS output.wav stream.snr\n"
                 "   or: %s input.SNS output.wav exact_sample_count [channels]\n",
                 argv[0], argv[0]);
    return EXIT_FAILURE;
  }

  try {
    const auto sns = ReadFile(argv[1]);

    const bool snr_mode = (argc == 4) && FileExists(argv[3]) &&
                          std::strtoull(argv[3], nullptr, 10) == 0;

    std::vector<std::uint8_t> packets;
    std::size_t exact_samples = 0;
    int source_channels = 2;

    if (snr_mode) {
      const SnrHeader snr = ParseSnr(ReadFile(argv[3]));
      g_sample_rate = snr.sample_rate;
      source_channels = snr.channels;
      exact_samples = snr.num_samples;
      packets = CombinePackets(snr, sns);
      std::fprintf(stderr,
                   "SNR: ch=%d rate=%d num_samples=%u prefetch=%u samples "
                   "(%zu bytes)\n",
                   snr.channels, snr.sample_rate, snr.num_samples,
                   snr.prefetch_samples, snr.prefetch.size());
    } else {
      // Legacy: caller supplies the (block-sum) sample count and channels.
      const unsigned long long parsed = std::strtoull(argv[3], nullptr, 10);
      if (parsed == 0 || parsed > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("invalid sample count");
      }
      exact_samples = static_cast<std::size_t>(parsed);
      source_channels = argc == 5 ? std::atoi(argv[4]) : 2;
      packets = RestorePackets(sns);
    }

    if (source_channels != 1 && source_channels != 2) {
      throw std::runtime_error("source channels must be 1 or 2");
    }

    const auto frames = ExtractFrames(packets);
    const auto pcm = DecodeFrames(frames, exact_samples, source_channels);
    WriteWav(argv[2], pcm);

    std::printf("decoded %zu XMA frames, wrote %zu samples (%.3f s)\n",
                frames.size(), exact_samples,
                static_cast<double>(exact_samples) / g_sample_rate);
    return EXIT_SUCCESS;
  } catch (const std::exception& error) {
    std::fprintf(stderr, "sns_xma_decode: %s\n", error.what());
    return EXIT_FAILURE;
  }
}
