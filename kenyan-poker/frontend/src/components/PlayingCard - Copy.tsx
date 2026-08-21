import type { CardView, Suit } from "../types";

const SUIT_SYMBOLS: Record<Suit, string> = {
  spades: "♠",
  hearts: "♥",
  diamonds: "♦",
  clubs: "♣",
};

const RED_SUITS = new Set<Suit>(["hearts", "diamonds"]);

interface PlayingCardProps {
  card: CardView;
  onClick?: () => void;
  disabled?: boolean;
  faceDown?: boolean;
}

export function PlayingCard({
  card,
  onClick,
  disabled,
  faceDown,
}: PlayingCardProps) {
  if (faceDown) {
    return (
      <div className="playing-card face-down" aria-hidden="true">
        <span className="face-down-emblem" />
      </div>
    );
  }

  const isJoker = card.rank === "JOKER";
  const isRed = card.suit ? RED_SUITS.has(card.suit) : false;
  const interactive = typeof onClick === "function";
  const symbol = isJoker ? "★" : SUIT_SYMBOLS[card.suit as Suit];

  const className = [
    "playing-card",
    isRed ? "red" : "black",
    isJoker ? "joker" : "",
    interactive ? "interactive" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const corner = (position: "tl" | "br") => (
    <span className={`corner corner-${position}`}>
      <span className="idx-rank">{isJoker ? "★" : card.rank}</span>
      {!isJoker && <span className="idx-suit">{symbol}</span>}
    </span>
  );

  const content = (
    <>
      {corner("tl")}
      <span className="center-pip">{symbol}</span>
      {isJoker && <span className="joker-label">JOKER</span>}
      {corner("br")}
    </>
  );

  if (!interactive) {
    return <div className={className}>{content}</div>;
  }

  return (
    <button
      type="button"
      className={className}
      onClick={onClick}
      disabled={disabled}
    >
      {content}
    </button>
  );
}
