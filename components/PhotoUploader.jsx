"use client";

import { useRef } from "react";

export default function PhotoUploader({ value, onChange }) {
  const inputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      onChange(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handlePickPhoto = () => {
    inputRef.current?.click();
  };

  return (
    <div>
      <button type="button" className="photoButton" onClick={handlePickPhoto}>
        {value ? (
          <img src={value} alt="Foto de perfil" className="photo" />
        ) : (
          <div className="photoHint">Sin foto</div>
        )}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
    </div>
  );
}
