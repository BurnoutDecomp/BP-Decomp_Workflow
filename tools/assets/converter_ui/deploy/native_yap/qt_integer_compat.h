#pragma once
#include <QDataStream>
#include <QDebug>
#include <cstdint>
#include <string>
#include <type_traits>

// On LP64 Linux, uint64_t is unsigned long but quint64 is unsigned long long.
// Qt's reference-taking stream operator cannot bind one to the other. Use a
// value conversion through Qt's exact-width type, preserving its endian handling.
// SFINAE leaves platforms where the aliases already agree entirely unchanged.
template<class T>
using NeedsQtInteger = std::enable_if_t<
    (std::is_same_v<T, std::uint64_t> && !std::is_same_v<T, quint64>) ||
    (std::is_same_v<T, std::int64_t> && !std::is_same_v<T, qint64>), int>;

template<class T, NeedsQtInteger<T> = 0>
inline QDataStream& operator>>(QDataStream& stream, T& value) {
    using QtInteger = std::conditional_t<std::is_signed_v<T>, qint64, quint64>;
    QtInteger raw = 0;
    stream >> raw;
    value = static_cast<T>(raw);
    return stream;
}

template<class T, NeedsQtInteger<T> = 0>
inline QDataStream& operator<<(QDataStream& stream, T value) {
    using QtInteger = std::conditional_t<std::is_signed_v<T>, qint64, quint64>;
    return stream << static_cast<QtInteger>(value);
}

#if QT_VERSION < QT_VERSION_CHECK(6, 5, 0)
// Ubuntu 24.04 supplies Qt 6.4, where std::string can ambiguously convert to
// both QByteArrayView and QUtf8StringView in YAP's diagnostic messages.
inline QDebug operator<<(QDebug debug, const std::string& value) {
    debug << QString::fromStdString(value);
    return debug;
}
#endif
