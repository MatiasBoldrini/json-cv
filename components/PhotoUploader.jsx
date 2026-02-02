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

  return (
    <div>
      {value ? (
        <img src={value} alt="Foto de perfil" className="photo" />
      ) : (
        <div className="photoHint">Sin foto</div>
      )}
      <div className="photoControls">
        <button
          type="button"
          className="toolbarButton"
          onClick={() => inputRef.current?.click()}
        >
          Cambiar foto
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
      </div>
      <div className="photoHint">Acepta URL o base64 en el JSON</div>
    </div>
  );
}
