import { ReactElement, JSXElementConstructor, useState, useEffect } from "react";
import {
  makeStyles,
  tokens,
  SearchBox,
  Dropdown,
  Option,
  Button as FluentButton,
} from "@fluentui/react-components";
import {
  ArrowSort20Regular,
  ArrowUp20Regular,
  ArrowDown20Regular,
} from "@fluentui/react-icons";

const useStyles = makeStyles({
  searchContainer: {
    marginTop: "48px",
    marginBottom: "16px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap", // Allow wrapping on smaller screens for accessibility
    width: "100%",
    minWidth: 0,
  },
  statusMessage: {
    marginBottom: "16px",
    fontSize: "14px",
    color: tokens.colorNeutralForeground3,
  },
  leftControls: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap", // Allow wrapping on smaller screens for accessibility
    flex: "1 1 auto", // Allow to grow and shrink but maintain minimum size
    minWidth: 0, // Allow shrinking below content size
    width: "100%",
  },
  searchBox: {
    width: "min(400px, 100%)",
    minWidth: 0,
    maxWidth: "100%", // Prevent overflow on small screens
    minHeight: "40px",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    flex: "1 1 auto", // Allow search box to be flexible
    "& input": {
      borderRadius: tokens.borderRadiusXLarge,
    },
  },
  filterDropdown: {
    minWidth: "140px",
    maxWidth: "100%",
    minHeight: "40px",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    flexShrink: 0, // Prevent dropdown from shrinking
    "& > div": {
      borderRadius: tokens.borderRadiusXLarge,
      border: "none",
      backgroundColor: "transparent",
    },
    "& input": {
      borderRadius: tokens.borderRadiusXLarge,
      border: "none",
      textDecoration: "none",
    },
    "& button": {
      border: "none",
      textDecoration: "none",
      borderRadius: tokens.borderRadiusXLarge,
    },
  },
  sortButton: {
    minWidth: "100px", // Ensure button is wide enough to show full text
    minHeight: "40px",
    padding: `${tokens.spacingVerticalSNudge} ${tokens.spacingHorizontalL}`,
    borderRadius: tokens.borderRadiusXLarge,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke1}`,
    backgroundColor: tokens.colorNeutralBackground1,
    flexShrink: 0, // Prevent button from shrinking
    whiteSpace: "nowrap", // Keep button text on one line
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },

  "@media (max-width: 640px)": {
    searchContainer: {
      alignItems: "stretch",
    },
    leftControls: {
      alignItems: "stretch",
      gap: tokens.spacingVerticalS,
    },
    searchBox: {
      width: "100%",
      minWidth: 0,
    },
    filterDropdown: {
      width: "100%",
      minWidth: 0,
      maxWidth: "100%",
      flex: "1 1 100%",
    },
    sortButton: {
      width: "100%",
      justifyContent: "center",
    },
  },
});

export type SortOrder = "none" | "asc" | "desc";

export interface FilterOption {
  key: string;
  placeholder: string;
  options: string[];
  selectedOptions: string[];
  onSelectionChange: (selectedOptions: string[]) => void;
  multiselect?: boolean;
  minWidth?: string;
}

export interface SearchFilterControlsProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  filters?: FilterOption[];
  sortOrder: SortOrder;
  onSortChange: () => void;
  sortLabel?: string;
  additionalControls?: ReactElement<any, string | JSXElementConstructor<any>>;
  resultsCount?: number;
  itemType?: string;
}

export function SearchFilterControls({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search",
  filters = [],
  sortOrder,
  onSortChange,
  sortLabel = "Sort",
  additionalControls,
  resultsCount,
  itemType = "results",
}: SearchFilterControlsProps) {
  const styles = useStyles();
  const [announcement, setAnnouncement] = useState("");

  // Announce search results changes for screen readers
  useEffect(() => {
    if (resultsCount !== undefined) {
      const message = resultsCount === 1
        ? `1 ${itemType.replace(/s$/, "")} found`
        : `${resultsCount} ${itemType} found`;
      
      // Update announcement with a delay to ensure screen readers detect the change
      const timeoutId = setTimeout(() => {
        setAnnouncement(message);
      }, 500);

      return () => clearTimeout(timeoutId);
    }
  }, [resultsCount, itemType]);

  // Helper function to create truncated display text for multiselect
  const getDisplayValue = (filter: FilterOption) => {
    // Return undefined when no selections to let placeholder show
    if (filter.selectedOptions.length === 0) {
      return undefined;
    }

    if (!filter.multiselect) {
      return filter.selectedOptions.join(", ");
    }

    const maxLength = 30; // Maximum characters to show
    const selectedText = filter.selectedOptions.join(", ");

    if (selectedText.length <= maxLength) {
      return selectedText;
    }

    // Show first item and count
    const firstItem = filter.selectedOptions[0];
    const remainingCount = filter.selectedOptions.length - 1;

    if (remainingCount === 1) {
      return `${firstItem}, +1 more`;
    } else {
      return `${firstItem}, +${remainingCount} more`;
    }
  };

  const getSortIcon = () => {
    switch (sortOrder) {
      case "asc":
        return <ArrowUp20Regular />;
      case "desc":
        return <ArrowDown20Regular />;
      default:
        return <ArrowSort20Regular />;
    }
  };

  const getSortTitle = () => {
    switch (sortOrder) {
      case "asc":
        return "Sorted A-Z";
      case "desc":
        return "Sorted Z-A";
      default:
        return `Sort by ${sortLabel.toLowerCase()}`;
    }
  };

  return (
    <>
      <div className={styles.searchContainer}>
        <div className={styles.leftControls}>
          <SearchBox
            appearance="outline"
            className={styles.searchBox}
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(_, data) => onSearchChange(data.value)}
          />
        {filters.map((filter) => {
          const displayValue = getDisplayValue(filter);
          const ariaLabel = displayValue 
            ? `${filter.placeholder}: ${displayValue}` 
            : filter.placeholder;
          
          return (
          <Dropdown
            key={filter.key}
            className={styles.filterDropdown}
            style={{ minWidth: filter.minWidth || "140px", maxWidth: "100%" }}
            placeholder={filter.placeholder}
            aria-label={ariaLabel}
            multiselect={filter.multiselect}
            value={displayValue}
            selectedOptions={filter.selectedOptions}
            onOptionSelect={(_, data) => {
              if (data.selectedOptions) {
                filter.onSelectionChange(data.selectedOptions);
              }
            }}
          >
            {filter.options.map((option) => (
              <Option key={option} value={option}>
                {option}
              </Option>
            ))}
          </Dropdown>
          );
        })}
        {additionalControls}
      </div>
      <FluentButton
        className={styles.sortButton}
        appearance="outline"
        icon={getSortIcon()}
        onClick={onSortChange}
        title={getSortTitle()}
      >
        {sortLabel}
      </FluentButton>
    </div>
    {resultsCount !== undefined && (
      <div 
        className={styles.statusMessage}
        role="status" 
        aria-live="assertive" 
        aria-atomic="true"
      >
        {announcement}
      </div>
    )}
    </>
  );
}
