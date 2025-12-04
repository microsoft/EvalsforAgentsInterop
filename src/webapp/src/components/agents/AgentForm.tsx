import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CircleNotch } from "@phosphor-icons/react";
import { Agent } from "@/lib/types";

interface AgentFormProps {
  mode: "create" | "edit";
  initialData?: Agent;
  onSubmit: (data: {
    name: string;
    description: string;
    model: string;
    agent_invocation_url: string;
  }) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export function AgentForm({
  mode,
  initialData,
  onSubmit,
  onCancel,
  isLoading = false,
}: AgentFormProps) {
  const [agentName, setAgentName] = useState(initialData?.name || "");
  const [agentModel, setAgentModel] = useState(initialData?.model || "");
  const [agentDescription, setAgentDescription] = useState(
    initialData?.description || ""
  );
  const [agentInvocationUrl, setAgentInvocationUrl] = useState(
    initialData?.agent_invocation_url || ""
  );

  // URL validation function
  const isValidUrl = (url: string): boolean => {
    if (!url.trim()) return false;
    try {
      const urlObj = new URL(url.trim());
      return urlObj.protocol === "http:" || urlObj.protocol === "https:";
    } catch {
      return false;
    }
  };

  const handleSubmit = async () => {
    await onSubmit({
      name: agentName.trim(),
      description: agentDescription.trim(),
      model: agentModel.trim(),
      agent_invocation_url: agentInvocationUrl.trim(),
    });
  };

  const isUrlValid = isValidUrl(agentInvocationUrl);
  const isValid =
    agentName.trim().length > 0 &&
    agentInvocationUrl.trim().length > 0 &&
    isUrlValid;

  return (
    <div className="space-y-4 py-4">
      <div className="space-y-2">
        <Label htmlFor="agent-name">Agent Name</Label>
        <Input
          id="agent-name"
          placeholder="e.g., GPT-4 Assistant"
          value={agentName}
          onChange={(e) => setAgentName(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="agent-invocation-url">Agent Invocation URL</Label>
        <Input
          id="agent-invocation-url"
          type="url"
          placeholder="e.g., https://api.example.com/agent/invoke"
          value={agentInvocationUrl}
          onChange={(e) => setAgentInvocationUrl(e.target.value)}
          disabled={isLoading}
          className={
            agentInvocationUrl.trim() && !isUrlValid
              ? ""
              : ""
          }
          style={agentInvocationUrl.trim() && !isUrlValid ? {
            borderColor: "#C4314B",
            boxShadow: "0 0 0 2px rgba(196, 49, 75, 0.2)"
          } : {}}
        />
        {agentInvocationUrl.trim() && !isUrlValid && (
          <p style={{ fontSize: "14px", color: "#C4314B" }}>
            Please enter a valid URL
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="model">Model</Label>
        <Input
          id="model"
          placeholder="e.g., gpt-4o, claude-3-opus"
          value={agentModel}
          onChange={(e) => setAgentModel(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          placeholder="Describe this agent's capabilities..."
          value={agentDescription}
          onChange={(e) => setAgentDescription(e.target.value)}
          rows={3}
          disabled={isLoading}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!isValid || isLoading}>
          {isLoading ? (
            <>
              <CircleNotch size={16} className="animate-spin mr-2" />
              {mode === "create" ? "Registering..." : "Updating..."}
            </>
          ) : mode === "create" ? (
            "Register Agent"
          ) : (
            "Update Agent"
          )}
        </Button>
      </div>
    </div>
  );
}
