import { Badge } from "@/components/ui/badge";

interface ScoreBadgeProps {
  score: number | string;
  className?: string;
  size?: "default" | "large";
}

export function ScoreBadge({
  score,
  className = "",
  size = "default",
}: ScoreBadgeProps) {
  const scoreNum = typeof score === "string" ? parseFloat(score) : score;
  const isGoodScore = scoreNum >= 70;

  const baseStyles = {
    display: "flex",
    width: "fit-content",
    padding: "2px 8px",
    justifyContent: "center",
    alignItems: "center",
    gap: "2px",
    flexShrink: 0,
    borderRadius: "4px",
  };

  const greenStyles = {
    ...baseStyles,
    background: "#F1FAF1",
    color: "#0D7717", // Green text color
  };

  const redStyles = {
    ...baseStyles,
    background: "#FDF6F6", 
    color: "#C4314B", // Red text color
  };

  const currentStyles = isGoodScore ? greenStyles : redStyles;

  return (
    <div
      style={currentStyles}
      className={`text-sm font-medium ${className}`}
    >
      {typeof score === "string" ? `${score}%` : `${scoreNum.toFixed(1)}%`}
    </div>
  );
}
