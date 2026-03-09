import { useParams, useNavigate } from "react-router-dom";
import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft20Regular,
  SpinnerIos20Regular,
  Wrench20Regular,
  ChartMultiple20Regular,
  NumberSymbol20Regular,
  Document20Regular,
  Chat20Regular,
  Checkmark20Regular,
  ArrowMinimize20Regular,
  ArrowMaximize20Regular,
  ClipboardCheckmark20Regular,
  Edit20Regular,
} from "@fluentui/react-icons";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import { useDataset } from "@/hooks/useDatasets";
import { SearchFilterControls } from "@/components/shared/SearchFilterControls";
import { NoDataCard } from "@/components/shared/NoDataCard";
import { useTableState } from "@/hooks/useTableState";
import { JsonEditor } from "@/components/shared/JsonEditor";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { useRubricsConfig } from "@/hooks/useRubricsConfig";
import { getKeyboardProps } from "@/hooks/useKeyboardClick";
import type {
  ToolExpectation,
  Rubric,
  ArgumentAssertion,
  BackendTestCase,
} from "@/lib/api";

interface BaseCardItem {
  id: string;
  type:
    | "tool"
    | "rubric"
    | "id"
    | "description"
    | "input"
    | "expected_response";
  title: string;
  content: string;
}

interface ToolExpectationCardItem extends BaseCardItem {
  type: "tool";
  toolName: string;
  toolCallArguments: ArgumentAssertion[];
}

interface RubricCardItem extends BaseCardItem {
  type: "rubric";
  rubricName: string;
  threshold: string;
  azureFoundryId: string;
  payload: Record<string, any>;
}

interface BasicInfoCardItem extends BaseCardItem {
  type: "id" | "description" | "input" | "expected_response";
}

type CardItem = ToolExpectationCardItem | RubricCardItem | BasicInfoCardItem;

export function TestCaseDetailPage() {
  const { id, testcase_id } = useParams<{ id: string; testcase_id: string }>();
  const navigate = useNavigate();
  const { dataset, loading, error, refetch } = useDataset(id!);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [isJsonEditMode, setIsJsonEditMode] = useState(false);
  const rubricsConfig = useRubricsConfig();

  const testCase = useMemo(() => {
    if (!dataset?.test_cases || !testcase_id) return null;
    return dataset.test_cases.find((tc) => tc.id === testcase_id);
  }, [dataset, testcase_id]);

  const handleUpdateTestCase = async (updatedTestCase: BackendTestCase) => {
    try {
      if (!testcase_id || !id) {
        throw new Error("Test case ID and dataset ID are required");
      }

      await apiClient.updateTestCase(id, testcase_id, updatedTestCase);
      await refetch(); // Refresh the dataset data to show updated test case
      toast.success("Test case updated successfully");
    } catch (error) {
      console.error("Error updating test case:", error);
      throw new Error(
        error instanceof Error ? error.message : "Failed to update test case"
      );
    }
  };

  const cardData = useMemo(() => {
    if (!testCase) return [];

    const items: CardItem[] = [];
    // Add tool expectations
    if (testCase.tool_expectations) {
      testCase.tool_expectations.forEach((toolExp, index) => {
        items.push({
          id: `tool-${index}`,
          type: "tool",
          title: `Tool: ${toolExp.name}`,
          content: toolExp.name,
          toolName: toolExp.name,
          toolCallArguments: toolExp.arguments || [],
        });
      });
    }

    // Add response quality rubrics (only if enabled)
    if (
      rubricsConfig.enabled &&
      testCase.response_quality_expectation?.rubrics
    ) {
      testCase.response_quality_expectation.rubrics.forEach((rubric, index) => {
        items.push({
          id: `rubric-${index}`,
          type: "rubric",
          title: `Response Quality Rubric: ${rubric.name}`,
          content: rubric.name,
          rubricName: rubric.name,
          threshold: `${(rubric.threshold * 100).toFixed(0)}%`,
          azureFoundryId: rubric.azure_foundry_id,
          payload: rubric.payload || {},
        });
      });
    }

    return items;
  }, [testCase, rubricsConfig.enabled]);

  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
  const [collapsedCards, setCollapsedCards] = useState<Set<string>>(new Set());

  const getCardIcon = (type: string) => {
    switch (type) {
      case "tool":
        return <Wrench20Regular className="text-primary" />;
      case "rubric":
        return <ChartMultiple20Regular className="text-primary" />;
      case "id":
        return <NumberSymbol20Regular className="text-primary" />;
      case "description":
        return <Document20Regular className="text-primary" />;
      case "input":
        return <Chat20Regular className="text-primary" />;
      case "expected_response":
        return <Checkmark20Regular className="text-primary" />;
      default:
        return null;
    }
  };

  const toggleCardCollapse = (cardId: string) => {
    setCollapsedCards((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(cardId)) {
        newSet.delete(cardId);
      } else {
        newSet.add(cardId);
      }
      return newSet;
    });
  };

  const {
    searchTerm,
    setSearchTerm,
    sortOrder,
    handleSort,
    filteredData: filteredCardData,
  } = useTableState({
    data: cardData,
    customSearchFunction: (item, searchTerm) =>
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.content.toLowerCase().includes(searchTerm.toLowerCase()),
    customSortFunction: (a, b, sortOrder) => {
      const comparison = a.title
        .toLowerCase()
        .localeCompare(b.title.toLowerCase());
      return sortOrder === "asc" ? comparison : -comparison;
    },
    filters: {
      type: {
        getValue: (item) => {
          switch (item.type) {
            case "tool":
              return "Tool";
            case "rubric":
              return "Response Quality Expectation";
            case "id":
              return "Id";
            case "description":
              return "Description";
            case "input":
              return "Input (Agent Prompt)";
            case "expected_response":
              return "Expected Output";
            default:
              return undefined;
          }
        },
        selectedValues: selectedFilters,
      },
    },
  });

  const toggleExpanded = (itemId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const renderCardContent = (item: CardItem) => {
    const isExpanded = expandedItems.has(item.id);
    const maxItemsToShow = 2;

    if (item.type === "tool") {
      const toolItem = item as ToolExpectationCardItem;
      const argumentsToShow = isExpanded
        ? toolItem.toolCallArguments
        : toolItem.toolCallArguments.slice(0, maxItemsToShow);
      const hasMore = toolItem.toolCallArguments.length > maxItemsToShow;

      return (
        <div className="space-y-3">
          <div className="text-sm bg-muted/50 p-3 rounded-md space-y-4">
            <p className="text-sm text-muted-foreground">Tool arguments</p>
            {argumentsToShow.map((arg, argIdx) => (
              <div key={argIdx} className="space-y-2">
                <div className="flex items-center gap-2">
                  <code className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">
                    {arg.name}
                  </code>
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <ClipboardCheckmark20Regular style={{ fontSize: "12px" }} />
                    Assertions ({arg.assertion.length})
                  </div>
                  <div className="space-y-1">
                    {arg.assertion.map((assertion, assertionIdx) => (
                      <p
                        key={assertionIdx}
                        className="text-xs text-muted-foreground"
                      >
                        • {assertion}
                      </p>
                    ))}
                  </div>
                </div>
                {rubricsConfig.enabled &&
                  arg.rubrics &&
                  arg.rubrics.length > 0 && (
                    <div className="space-y-2 mt-2">
                      <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <ChartMultiple20Regular style={{ fontSize: "12px" }} />
                        Rubrics ({arg.rubrics.length})
                      </div>
                      {arg.rubrics.map((rubric, rIdx) => (
                        <Collapsible key={rIdx}>
                          <CollapsibleTrigger asChild>
                            <div className="cursor-pointer hover:bg-muted/50 p-2 rounded-md transition-colors">
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 flex-1">
                                  <Badge
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
                                      color: "#525252",
                                      border: "none",
                                      fontSize: "12px",
                                    }}
                                  >
                                    {rubric.name}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">
                                    Threshold:{" "}
                                    {(rubric.threshold * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <span className="text-xs text-muted-foreground">
                                  ▼
                                </span>
                              </div>
                            </div>
                          </CollapsibleTrigger>
                          <CollapsibleContent className="mt-1">
                            <div className="bg-background/50 p-3 rounded-md space-y-2 text-xs">
                              <div>
                                <span className="font-medium">
                                  Azure Foundry ID:
                                </span>{" "}
                                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                                  {rubric.azure_foundry_id}
                                </code>
                              </div>
                              <div>
                                <span className="font-medium">Threshold:</span>{" "}
                                {rubric.threshold} (
                                {(rubric.threshold * 100).toFixed(0)}%)
                              </div>
                              {rubric.payload &&
                                Object.keys(rubric.payload).length > 0 && (
                                  <div>
                                    <span className="font-medium">
                                      Payload:
                                    </span>
                                    <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto">
                                      {JSON.stringify(rubric.payload, null, 2)}
                                    </pre>
                                  </div>
                                )}
                            </div>
                          </CollapsibleContent>
                        </Collapsible>
                      ))}
                    </div>
                  )}
              </div>
            ))}
            {hasMore && (
              <div className="flex justify-center pt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleExpanded(item.id)}
                >
                  {isExpanded
                    ? "Show Less"
                    : `Show More (${
                        toolItem.toolCallArguments.length - maxItemsToShow
                      })`}
                </Button>
              </div>
            )}
          </div>
        </div>
      );
    } else if (item.type === "rubric") {
      const rubricItem = item as RubricCardItem;
      const payloadEntries = Object.entries(rubricItem.payload);
      const entriesToShow = isExpanded
        ? payloadEntries
        : payloadEntries.slice(0, maxItemsToShow);
      const hasMore = payloadEntries.length > maxItemsToShow;

      return (
        <div className="space-y-3">
          <div className="text-sm bg-muted/50 p-3 rounded-md space-y-3">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">
                Azure Foundry ID: {rubricItem.azureFoundryId}
              </div>
            </div>
            {entriesToShow.length > 0 ? (
              <div className="space-y-2 pt-3">
                <div className="text-xs font-medium text-muted-foreground">
                  Payload Properties:
                </div>
                {entriesToShow.map(([key, value], idx) => (
                  <div key={idx} className="space-y-1">
                    <code className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">
                      {key}
                    </code>
                    <pre className="text-xs bg-background/50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  </div>
                ))}
                {hasMore && (
                  <div className="flex justify-center pt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleExpanded(item.id)}
                    >
                      {isExpanded
                        ? "Show Less"
                        : `Show More (${
                            payloadEntries.length - maxItemsToShow
                          })`}
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground pt-3">
                No payload properties
              </div>
            )}
          </div>
        </div>
      );
    } else {
      // Basic info cards
      return (
        <div className="space-y-2">
          <div className="text-sm bg-muted/50 p-3 rounded-md whitespace-pre-wrap max-h-[200px] overflow-y-auto">
            {item.content}
          </div>
        </div>
      );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <SpinnerIos20Regular
          className="animate-spin text-primary mb-4"
          style={{ fontSize: "48px" }}
        />
        <p className="text-muted-foreground">Loading test case...</p>
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
          <ArrowLeft20Regular />
          Back to Datasets
        </Button>
      </div>
    );
  }

  if (!dataset || !testCase) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-2xl font-bold mb-2">Test case not found</h2>
        <p className="text-muted-foreground mb-6">
          The test case you're looking for doesn't exist.
        </p>
        <Button
          onClick={() => navigate(`/datasets/${id}`)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft20Regular />
          Back to Dataset
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <Breadcrumb aria-label="Test case navigation" className="mb-4">
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
                  <BreadcrumbButton onClick={() => navigate(`/datasets/${id}`)}>
                    {truncateBreadcrumbLongName(
                      dataset.seed?.name ||
                        dataset.metadata?.suite_id ||
                        "Dataset"
                    )}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton onClick={() => navigate(`/datasets/${id}`)}>
                  {dataset.seed?.name ||
                    dataset.metadata?.suite_id ||
                    "Dataset"}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
            <BreadcrumbDivider />
            <BreadcrumbItem>
              {isTruncatableBreadcrumbContent(
                testCase.name || `Test Case ${testcase_id}`,
                30
              ) ? (
                <Tooltip
                  withArrow
                  content={testCase.name || `Test Case ${testcase_id}`}
                  relationship="label"
                >
                  <BreadcrumbButton current>
                    {truncateBreadcrumbLongName(
                      testCase.name || `Test Case ${testcase_id}`
                    )}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton current>
                  {testCase.name || `Test Case ${testcase_id}`}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
          </Breadcrumb>
          <h1 className="text-3xl font-bold tracking-tight">
            {testCase.name || `Test Case ${testcase_id}`}
          </h1>
          <p className="text-muted-foreground text-sm">
            {testCase.description}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={isJsonEditMode ? "default" : "outline"}
            onClick={() => setIsJsonEditMode(!isJsonEditMode)}
            className="gap-2"
          >
            <Edit20Regular style={{ fontSize: "14px" }} />
            {isJsonEditMode ? "View Mode" : "JSON Edit Mode"}
          </Button>
        </div>
      </div>

      {isJsonEditMode ? (
        <div className="space-y-6">
          <JsonEditor
            title="Test Case JSON"
            data={testCase}
            onSave={handleUpdateTestCase}
            maxHeight="700px"
            protectedFields={["id", "dataset_id"]}
          />
          <Alert>
            <AlertDescription>
              You are editing the complete test case JSON. All changes will be
              saved when you click "Save Changes" in the editor. Note: The "id"
              and "dataset_id" fields cannot be modified.
            </AlertDescription>
          </Alert>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Input (Agent Prompt)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className="text-sm bg-muted/50 p-3 rounded-md whitespace-pre-wrap max-h-[300px] overflow-y-auto"
                  style={{ minHeight: "120px" }}
                >
                  {testCase.input}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Expected Response
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className="text-sm bg-muted/50 p-3 rounded-md whitespace-pre-wrap max-h-[300px] overflow-y-auto"
                  style={{ minHeight: "120px" }}
                >
                  {testCase.expected_response}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Test Case Information</h2>

            {cardData.length === 0 ? (
              <NoDataCard
                icon={
                  <Wrench20Regular
                    className="text-muted-foreground mb-4"
                    style={{ fontSize: "48px" }}
                  />
                }
                title="No information available"
                description="This test case has no available information."
              />
            ) : (
              <>
                <SearchFilterControls
                  searchValue={searchTerm}
                  onSearchChange={setSearchTerm}
                  searchPlaceholder="Search test case information"
                  filters={[
                    {
                      key: "type",
                      placeholder: "Filter by type",
                      options: [
                        "Tool",
                        ...(rubricsConfig.enabled
                          ? ["Response Quality Expectation"]
                          : []),
                        "Id",
                        "Description",
                        "Input (Agent Prompt)",
                        "Expected Output",
                      ],
                      selectedOptions: selectedFilters,
                      onSelectionChange: setSelectedFilters,
                      multiselect: true,
                    },
                  ]}
                  sortOrder={sortOrder}
                  onSortChange={handleSort}
                  sortLabel="Sort"
                />
                <div className="space-y-3">
                  {filteredCardData.map((item) => {
                    const isCollapsed = collapsedCards.has(item.id);
                    const keyboardProps = getKeyboardProps(() => toggleCardCollapse(item.id));

                    return (
                      <Card
                        key={item.id}
                        className="transition-all hover:shadow-md hover:border-primary/50 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                        {...keyboardProps}
                      >
                        <CardHeader className="pb-1">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                {getCardIcon(item.type)}
                                <CardTitle className="text-lg">
                                  {item.title}
                                </CardTitle>
                              </div>
                              {item.type === "tool" &&
                                item.toolCallArguments && (
                                  <CardDescription className="mt-1">
                                    {item.toolCallArguments.length} argument
                                    {item.toolCallArguments.length !== 1
                                      ? "s"
                                      : ""}
                                  </CardDescription>
                                )}
                              {item.type === "rubric" && item.threshold && (
                                <CardDescription className="mt-1">
                                  Threshold: {item.threshold}
                                </CardDescription>
                              )}
                            </div>
                            <div className="text-muted-foreground transition-transform duration-200">
                              {isCollapsed ? (
                                <ArrowMaximize20Regular
                                  style={{ fontSize: "14px" }}
                                />
                              ) : (
                                <ArrowMinimize20Regular
                                  style={{ fontSize: "14px" }}
                                />
                              )}
                            </div>
                          </div>
                        </CardHeader>
                        {!isCollapsed && (
                          <CardContent>{renderCardContent(item)}</CardContent>
                        )}
                      </Card>
                    );
                  })}
                </div>
                {filteredCardData.length === 0 && (
                  <NoDataCard
                    icon={
                      <Wrench20Regular
                        className="text-muted-foreground mb-4"
                        style={{ fontSize: "48px" }}
                      />
                    }
                    title={`No items found matching "${searchTerm}"`}
                    description="Try adjusting your search terms or filters"
                  />
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
