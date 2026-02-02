"use client";

import ContentEditable from "react-contenteditable";
import { useRef } from "react";

export default function EditableText({
  value,
  onChange,
  tagName = "span",
  className = ""
}) {
  const contentRef = useRef(null);
  const html = value ?? "";

  return (
    <ContentEditable
      innerRef={contentRef}
      html={html}
      tagName={tagName}
      className={`editable ${className}`}
      onChange={(event) => {
        const text = event.target.value
          .replace(/<br>/g, "\n")
          .replace(/<[^>]+>/g, "");
        onChange(text);
      }}
    />
  );
}
