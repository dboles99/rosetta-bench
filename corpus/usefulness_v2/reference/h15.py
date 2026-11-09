def parse_csv_line(line, delimiter=",", quote='"'):
    fields = []
    i, n = 0, len(line)
    while True:
        if i < n and line[i] == quote:
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quoted field")
                ch = line[i]
                if ch == quote:
                    if i + 1 < n and line[i + 1] == quote:
                        buf.append(quote)
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(ch)
                i += 1
            fields.append("".join(buf))
            if i == n:
                return fields
            if line[i] != delimiter:
                raise ValueError("unexpected character after closing quote")
            i += 1
        else:
            j = line.find(delimiter, i)
            if j == -1:
                fields.append(line[i:])
                return fields
            fields.append(line[i:j])
            i = j + 1


def format_csv_line(fields, delimiter=",", quote='"'):
    out = []
    for field in fields:
        needs_quotes = (delimiter in field or quote in field or "\n" in field or "\r" in field
                        or field[:1] == " " or field[-1:] == " ")
        out.append(quote + field.replace(quote, quote * 2) + quote if needs_quotes else field)
    return delimiter.join(out)
