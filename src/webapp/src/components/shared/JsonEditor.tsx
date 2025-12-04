import { useState } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Edit20Regular,
  Save20Regular,
  Dismiss20Regular,
  Warning20Regular,
} from "@fluentui/react-icons";

interface JsonEditorProps {
  title: string;
  data: any;
  onSave: (newData: any) => Promise<void> | void;
  readOnly?: boolean;
  maxHeight?: string;
  protectedFields?: string[];
}

export function JsonEditor({
  title,
  data,
  onSave,
  readOnly = false,
  maxHeight = "400px",
  protectedFields = [],
}: JsonEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<string>("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleStartEdit = () => {
    setEditData(JSON.stringify(data, null, 2));
    setValidationError(null);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setEditData("");
    setValidationError(null);
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      // Validate that the data is valid JSON
      const parsedData = JSON.parse(editData);

      // Check if any protected fields have been changed
      if (protectedFields.length > 0) {
        const changedProtectedFields: string[] = [];
        for (const field of protectedFields) {
          if (data[field] !== parsedData[field]) {
            changedProtectedFields.push(field);
          }
        }

        if (changedProtectedFields.length > 0) {
          setValidationError(
            `Cannot modify protected fields: ${changedProtectedFields.join(
              ", "
            )}. These fields are read-only.`
          );
          return;
        }
      }

      await onSave(parsedData);
      setIsEditing(false);
      setEditData("");
      setValidationError(null);
    } catch (error) {
      setValidationError(
        error instanceof Error ? error.message : "Invalid JSON data"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleTextChange = (value: string | undefined) => {
    const newValue = value || "";
    setEditData(newValue);
    try {
      const parsedData = JSON.parse(newValue);

      // Check if any protected fields have been changed
      if (protectedFields.length > 0) {
        const changedProtectedFields: string[] = [];
        for (const field of protectedFields) {
          if (data[field] !== parsedData[field]) {
            changedProtectedFields.push(field);
          }
        }

        if (changedProtectedFields.length > 0) {
          setValidationError(
            `Cannot modify protected fields: ${changedProtectedFields.join(
              ", "
            )}. These fields are read-only.`
          );
          return;
        }
      }

      setValidationError(null);
    } catch (error) {
      setValidationError(
        error instanceof Error ? error.message : "Invalid JSON"
      );
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          {!readOnly && (
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                    className="gap-2"
                  >
                    <Dismiss20Regular style={{ fontSize: "14px" }} />
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={!!validationError || isSaving}
                    size="sm"
                    className="gap-2"
                  >
                    <Save20Regular style={{ fontSize: "14px" }} />
                    {isSaving ? "Saving..." : "Save"}
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartEdit}
                  className="gap-2"
                >
                  <Edit20Regular style={{ fontSize: "14px" }} />
                  Edit
                </Button>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {validationError && (
          <Alert variant="destructive" className="mb-4">
            <Warning20Regular className="h-4 w-4" />
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}

        <div
          className="border rounded-md overflow-auto bg-muted/20"
          style={{ maxHeight }}
        >
          {isEditing ? (
            <Editor
              key="edit-mode"
              height={maxHeight}
              defaultLanguage="json"
              value={editData}
              onChange={handleTextChange}
              options={{
                readOnly: false, // Explicitly set to false for editing mode
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 12,
                lineNumbers: "on",
                wordWrap: "on",
                automaticLayout: true,
                tabSize: 2,
                insertSpaces: true,
                formatOnPaste: true,
                formatOnType: true,
                bracketPairColorization: { enabled: true },
                suggest: {
                  showKeywords: false,
                  showSnippets: false,
                },
                quickSuggestions: false,
                folding: true,
                foldingHighlight: true,
                showFoldingControls: "always",
                renderValidationDecorations: "on",
              }}
              theme="vs"
            />
          ) : (
            <Editor
              key="view-mode"
              height={maxHeight}
              language="json"
              value={JSON.stringify(data, null, 2)}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                lineNumbers: "on",
                automaticLayout: true,
                tabSize: 2,
                insertSpaces: true,
                formatOnPaste: true,
                formatOnType: true,
                folding: true,
                foldingHighlight: true,
                showFoldingControls: "always",
                fontSize: 12,
                fontFamily:
                  'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Inconsolata, "Roboto Mono", monospace',
                padding: { top: 12, bottom: 12 },
                renderValidationDecorations: "off", // Turn off validation decorations in read-only mode
              }}
              theme="vs"
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
