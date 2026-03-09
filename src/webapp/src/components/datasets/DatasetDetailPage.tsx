import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ArrowLeft, CircleNotch, Wrench } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbDivider,
  BreadcrumbButton,
  makeStyles,
  Tooltip,
  isTruncatableBreadcrumbContent,
  truncateBreadcrumbLongName,
} from "@fluentui/react-components";
import { AIContentDisclaimer } from "@/components/shared/AIContentDisclaimer";
import { useDataset } from "@/hooks/useDatasets";
import { getKeyboardProps } from "@/hooks/useKeyboardClick";

const useBreadcrumbStyles = makeStyles({
  // Remove custom styles since we're using Fluent UI's built-in truncation
});

export function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const breadcrumbStyles = useBreadcrumbStyles();
  const { dataset, loading, error } = useDataset(id!);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <CircleNotch size={48} className="animate-spin text-primary mb-4" />
        <p className="text-muted-foreground">Loading dataset...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
        <Alert variant="destructive" className="max-w-md mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button
          onClick={() => navigate("/datasets")}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft size={18} />
          Back to Datasets
        </Button>
      </div>
    );
  }

  if (!dataset || !dataset.test_cases) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-2xl font-bold mb-2">Dataset not found</h2>
        <p className="text-muted-foreground mb-6">
          The dataset you're looking for doesn't exist.
        </p>
        <Button
          onClick={() => navigate("/datasets")}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft size={18} />
          Back to Datasets
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <Breadcrumb aria-label="Dataset navigation" className="mb-4">
            <BreadcrumbItem>
              {isTruncatableBreadcrumbContent("Datasets", 30) ? (
                <Tooltip withArrow content="Datasets" relationship="label">
                  <BreadcrumbButton onClick={() => navigate("/datasets")}>
                    {truncateBreadcrumbLongName("Datasets")}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton onClick={() => navigate("/datasets")}>
                  Datasets
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
            <BreadcrumbDivider />
            <BreadcrumbItem>
              {isTruncatableBreadcrumbContent(
                dataset.seed?.name || dataset.metadata?.suite_id || "Dataset",
                30
              ) ? (
                <Tooltip
                  withArrow
                  content={
                    dataset.seed?.name ||
                    dataset.metadata?.suite_id ||
                    "Dataset"
                  }
                  relationship="label"
                >
                  <BreadcrumbButton current>
                    {truncateBreadcrumbLongName(
                      dataset.seed?.name ||
                        dataset.metadata?.suite_id ||
                        "Dataset"
                    )}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton current>
                  {dataset.seed?.name ||
                    dataset.metadata?.suite_id ||
                    "Dataset"}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
          </Breadcrumb>
          <h1 className="text-3xl font-bold tracking-tight">
            {dataset.seed?.name || dataset.metadata?.suite_id || "Dataset"}
          </h1>
          <p className="text-muted-foreground text-sm">{dataset.seed?.goal}</p>
          <p className="text-muted-foreground text-xs">
            Generator: {dataset.metadata?.generator_id} • Version:{" "}
            {dataset.metadata?.version}
          </p>
          <AIContentDisclaimer />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Test Cases
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {dataset.test_cases?.length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Created
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">
              {new Date(
                dataset.metadata?.created_at || dataset.created_at
              ).toLocaleDateString()}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Test Cases</h2>

        {dataset.test_cases.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground">No test cases yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {(dataset.test_cases || []).map((testCase, index) => {
              const keyboardProps = getKeyboardProps(() =>
                navigate(`/datasets/${id}/testcases/${testCase.id}`)
              );
              return (
              <Card
                key={testCase.id}
                className="cursor-pointer transition-all hover:shadow-md hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                {...keyboardProps}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <CardTitle className="text-lg">
                        {testCase.name || `Test Case ${testCase.id}`}
                      </CardTitle>
                      <CardDescription className="line-clamp-2">
                        {testCase.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-1.5">
                      Input
                    </h4>
                    <p className="text-sm bg-muted/50 p-2 rounded-md line-clamp-2">
                      {testCase.input}
                    </p>
                  </div>

                  {testCase.minimal_tool_set &&
                    testCase.minimal_tool_set.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-muted-foreground mb-1.5 flex items-center gap-1.5">
                          <Wrench size={14} />
                          Required Tools
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {testCase.minimal_tool_set.map((tool, idx) => (
                            <Badge
                              key={idx}
                              variant="outline"
                              style={{
                                display: "flex",
                                minWidth: "103px",
                                padding: "2px 4px",
                                justifyContent: "center",
                                alignItems: "center",
                                gap: "2px",
                                flexShrink: 0,
                                borderRadius: "4px",
                                background: "#EBEBEB",
                                color: "#6B7280",
                                border: "none",
                                fontSize: "12px",
                              }}
                            >
                              {tool}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-1.5">
                      Expected Response
                    </h4>
                    <div className="text-sm bg-muted/50 p-2 rounded-md overflow-hidden relative max-h-[4.5rem]">
                      <p className="line-clamp-3">
                        {testCase.expected_response}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
