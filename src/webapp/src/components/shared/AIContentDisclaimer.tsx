import { Warning20Regular } from "@fluentui/react-icons";

interface AIContentDisclaimerProps {
  className?: string;
  iconSize?: string;
  textSize?: string;
}

export function AIContentDisclaimer({
  className = "flex items-center gap-2 mt-1",
  iconSize = "14px",
  textSize = "text-xs",
}: AIContentDisclaimerProps) {
  return (
    <div className={className}>
      <Warning20Regular
        className="text-gray-500"
        style={{ fontSize: iconSize }}
      />
      <p className={`${textSize} text-muted-foreground`}>
        AI generated content may be incorrect
      </p>
    </div>
  );
}
