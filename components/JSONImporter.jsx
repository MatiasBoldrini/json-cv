"use client";

import { useEffect, useState } from "react";

export default function JSONImporter({ onImport, initialValue }) {
  const [isOpen, setIsOpen] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (isOpen && !value && initialValue) {
      setValue(initialValue);
    }
  }, [isOpen, value, initialValue]);

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
      <button type="button" className="toolbarButton" onClick={() => setIsOpen(true)}>
        Importar JSON
      </button>
      {isOpen ? (
        <div className="jsonModalOverlay" onClick={() => setIsOpen(false)}>
          <div
            className="jsonModal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="jsonModalHeader">
              <div className="jsonModalTitle">Editar JSON del CV</div>
              <button
                type="button"
                className="jsonModalClose"
                onClick={() => setIsOpen(false)}
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>
            <div className="jsonModalBody">
              <textarea
                placeholder="Pegá aquí tu JSON de resume..."
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
              {error ? <div className="jsonError">{error}</div> : null}
            </div>
            <div className="jsonModalFooter">
              <button
                type="button"
                className="toolbarButton"
                onClick={() => setValue(initialValue || "")}
              >
                Restaurar por defecto
              </button>
              <div className="jsonModalActions">
                <button type="button" className="toolbarButton" onClick={handleImport}>
                  Aplicar JSON
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
