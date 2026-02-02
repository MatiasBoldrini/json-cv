"use client";

import { useState } from "react";

export default function JSONImporter({ onImport }) {
  const [isOpen, setIsOpen] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  const handleImport = () => {
    setError("");
    try {
      const parsed = JSON.parse(value);
      onImport(parsed);
      setIsOpen(false);
      setValue("");
    } catch (err) {
      setError("El JSON no es válido.");
    }
  };

  return (
    <div>
      <button
        type="button"
        className="toolbarButton"
        onClick={() => setIsOpen((prev) => !prev)}
      >
        {isOpen ? "Cerrar JSON" : "Importar JSON"}
      </button>
      {isOpen ? (
        <div className="jsonPanel">
          <textarea
            placeholder="Pegá aquí tu JSON de resume..."
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <div className="photoControls">
            <button type="button" className="toolbarButton" onClick={handleImport}>
              Aplicar JSON
            </button>
          </div>
          {error ? <div className="jsonError">{error}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
