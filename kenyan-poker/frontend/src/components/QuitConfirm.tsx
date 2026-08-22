interface QuitConfirmProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function QuitConfirm({ onConfirm, onCancel }: QuitConfirmProps) {
  return (
    <div className="suit-picker-overlay">
      <div className="suit-picker quit-confirm">
        <p>Quit this game?</p>
        <p className="hint">
          Your hand goes back into the draw pile and the game carries on
          without you. This can't be undone.
        </p>
        <div className="quit-confirm-actions">
          <button type="button" className="btn-danger" onClick={onConfirm}>
            Quit game
          </button>
          <button type="button" className="cancel" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
