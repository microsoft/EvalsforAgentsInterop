import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FileText, CircleNotch, DotsThree, Trash } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { useDatasets } from "@/hooks/useDatasets";
import { apiClient } from "@/lib/api";
import { Button as FluentButton, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem } from "@fluentui/react-components";
import { MoreHorizontal20Regular, FolderOpen20Regular, Delete20Regular } from "@fluentui/react-icons";
import { DataTable, TableColumn } from "@/components/shared/DataTable";
import { SearchFilterControls } from "@/components/shared/SearchFilterControls";
import { NoDataCard } from "@/components/shared/NoDataCard";
import { useTableState } from "@/hooks/useTableState";

export function DatasetsPage() {
	const navigate = useNavigate();
	const { datasets, loading, error, refetch } = useDatasets();
	const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
	const [datasetToDelete, setDatasetToDelete] = useState<any>(null);
	const [isDeleting, setIsDeleting] = useState(false);

	const {
		searchTerm,
		setSearchTerm,
		sortOrder,
		handleSort,
		filteredData: filteredDatasets,
	} = useTableState({
		data: datasets,
		customSearchFunction: (dataset, searchTerm) => dataset.seed?.name?.toLowerCase().includes(searchTerm.toLowerCase()) || false,
		customSortFunction: (a, b, sortOrder) => {
			const aName = a.seed?.name?.toLowerCase() || "";
			const bName = b.seed?.name?.toLowerCase() || "";
			const comparison = aName.localeCompare(bName);
			return sortOrder === "asc" ? comparison : -comparison;
		},
	});

	const columns: TableColumn[] = [
		{
			key: "name",
			header: "Dataset name",
			width: "60%",
			minWidth: "250px",
			render: (dataset: any) => (
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						gap: "2px",
						paddingRight: "16.0%",
						boxSizing: "border-box",
					}}
				>
					<div style={{ fontWeight: 600, fontSize: "14px" }}>{dataset.seed.name}</div>
					<div
						style={{
							fontSize: "12px",
							color: "#6b7280",
							display: "-webkit-box",
							WebkitLineClamp: 2,
							WebkitBoxOrient: "vertical",
							overflow: "hidden",
							textOverflow: "ellipsis",
						}}
					>
						{dataset.seed.goal}
					</div>
				</div>
			),
		},
		{
			key: "created",
			header: "Created",
			width: "15%",
			minWidth: "120px",
			render: (dataset: any) => new Date(dataset.metadata?.created_at || dataset.created_at).toLocaleDateString(),
		},
		{
			key: "testCases",
			header: "Test cases",
			width: "20%",
			minWidth: "140px",
			render: (dataset: any) => {
				const testCasesCount = dataset.test_case_ids?.length || 0;
				return (
					<Badge
						variant="secondary"
						style={{
							display: "flex",
							width: "103px",
							padding: "2px 4px",
							justifyContent: "center",
							alignItems: "center",
							gap: "2px",
							flexShrink: 0,
							borderRadius: "4px",
							background: "#EBEBEB",
							color: "#6B7280",
							border: "none",
						}}
					>
						{testCasesCount} test cases
					</Badge>
				);
			},
		},
		{
			key: "actions",
			header: "",
			width: "5%",
			minWidth: "60px",
			render: (dataset: any) => (
				<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
					<DropdownMenu>
						<DropdownMenuTrigger asChild>
							<Button variant="ghost" size="sm" onClick={(e) => e.stopPropagation()}>
								<DotsThree size={16} />
							</Button>
						</DropdownMenuTrigger>
						<DropdownMenuContent align="end">
							<DropdownMenuItem
								onClick={(e) => {
									e.stopPropagation();
									handleOpenDataset(dataset);
								}}
							>
								<FolderOpen20Regular className="mr-2" />
								Open Dataset
							</DropdownMenuItem>
							<DropdownMenuItem
								onClick={(e) => {
									e.stopPropagation();
									handleDeleteDataset(dataset);
								}}
								variant="destructive"
							>
								<Trash size={16} className="mr-2" />
								Delete Dataset
							</DropdownMenuItem>
						</DropdownMenuContent>
					</DropdownMenu>
				</div>
			),
		},
	];

	const handleOpenDataset = (dataset: any) => {
		navigate(`/datasets/${dataset.id}`);
	};

	const handleDeleteDataset = (dataset: any) => {
		setDatasetToDelete(dataset);
		setDeleteDialogOpen(true);
	};

	const confirmDeleteDataset = async () => {
		if (!datasetToDelete) return;

		setIsDeleting(true);
		try {
			await apiClient.deleteDataset(datasetToDelete.id);
			toast.success("Dataset deleted successfully");
			setDeleteDialogOpen(false);
			setDatasetToDelete(null);
			refetch();
		} catch (error) {
			console.error("Error deleting dataset:", error);
			toast.error("Failed to delete dataset");
		} finally {
			setIsDeleting(false);
		}
	};

	if (loading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh]">
				<CircleNotch size={48} className="animate-spin text-primary mb-4" />
				<p className="text-muted-foreground">Loading evaluation datasets...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div className="space-y-6">
				<div className="flex items-center justify-between">
					<div>
						<h1 className="text-3xl font-bold tracking-tight">Evaluation Datasets</h1>
						<p className="text-muted-foreground mt-1">Manage test datasets and evaluation criteria for AI agents</p>
					</div>
				</div>
				<NoDataCard
					icon={<FileText size={48} className="text-muted-foreground mb-4" />}
					title="Failed to load datasets"
					description={`Please try again later. ${error}`}
				/>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-3xl font-bold tracking-tight">Evaluation Datasets</h1>
					<p className="text-muted-foreground mt-1">Manage test suites for evaluating AI agent capabilities</p>
				</div>
			</div>

			{datasets.length === 0 ? (
				<NoDataCard
					icon={
						<div className="bg-muted rounded-full p-6 mb-6">
							<FileText size={48} className="text-muted-foreground" />
						</div>
					}
					title="No datasets yet"
					description="Upload evaluation datasets to start testing AI agents."
				/>
			) : (
				<>
					<SearchFilterControls
						searchValue={searchTerm}
						onSearchChange={setSearchTerm}
						searchPlaceholder="Search datasets"
						filters={[]}
						sortOrder={sortOrder}
						onSortChange={handleSort}
						sortLabel="Sort"
					/>
					<DataTable
						columns={columns}
						data={filteredDatasets}
						onRowClick={(dataset) => navigate(`/datasets/${dataset.id}`)}
						emptyState={
							<NoDataCard
								icon={<FileText size={48} className="text-muted-foreground mb-4" />}
								title={`No datasets found matching "${searchTerm}"`}
								description="Try adjusting your search terms"
							/>
						}
					/>
				</>
			)}

			{/* Delete Dataset Confirmation */}
			<AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Delete Dataset</AlertDialogTitle>
						<AlertDialogDescription>
							Are you sure you want to delete "{datasetToDelete?.seed?.name}"? This action cannot be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel
							onClick={() => {
								setDeleteDialogOpen(false);
								setDatasetToDelete(null);
							}}
						>
							Cancel
						</AlertDialogCancel>
						<AlertDialogAction
							onClick={confirmDeleteDataset}
							disabled={isDeleting}
							className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							{isDeleting ? (
								<>
									<CircleNotch size={16} className="animate-spin mr-2" />
									Deleting...
								</>
							) : (
								"Delete Dataset"
							)}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
