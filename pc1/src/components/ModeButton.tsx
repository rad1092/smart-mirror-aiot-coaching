import type { ModeType } from "../pages/ModePage";

type ModeButtonProps = {
  mode: ModeType;
  label: string;
  description?: string;
  onClick: (mode: ModeType) => void;
};

function ModeButton({ mode, label, description, onClick }: ModeButtonProps) {
  return (
    <button
      type="button"
      className="mode-button"
      onClick={() => onClick(mode)}
      aria-label={`${label} 모드 선택`}
    >
      <span className="mode-button__label">{label}</span>
      {description ? <span className="mode-button__desc">{description}</span> : null}
    </button>
  );
}

export default ModeButton;
