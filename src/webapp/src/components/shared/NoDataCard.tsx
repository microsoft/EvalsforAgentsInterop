import { ReactElement, JSXElementConstructor } from "react";
import { Card, CardContent } from "@/components/ui/card";

export interface NoDataCardProps {
  icon: ReactElement<any, string | JSXElementConstructor<any>>;
  title: string;
  description?: string;
  action?: ReactElement<any, string | JSXElementConstructor<any>>;
}

export function NoDataCard({
  icon,
  title,
  description,
  action,
}: NoDataCardProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        {icon}
        <p className="text-muted-foreground mb-4">{title}</p>
        {description && (
          <p className="text-sm text-muted-foreground mb-4">{description}</p>
        )}
        {action}
      </CardContent>
    </Card>
  );
}
