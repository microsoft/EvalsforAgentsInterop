import { useState, useMemo } from "react";

export type SortOrder = "none" | "asc" | "desc";

export interface UseTableStateOptions<T> {
  data: T[];
  searchFields?: (keyof T)[];
  defaultSortField?: keyof T;
  initialSortOrder?: SortOrder;
  customSearchFunction?: (item: T, searchTerm: string) => boolean;
  customSortFunction?: (a: T, b: T, sortOrder: SortOrder) => number;
  filters?: {
    [key: string]: {
      getValue: (item: T) => string | undefined;
      selectedValues: string[];
    };
  };
}

export function useTableState<T>({
  data,
  searchFields = [],
  defaultSortField,
  initialSortOrder = "none",
  customSearchFunction,
  customSortFunction,
  filters = {},
}: UseTableStateOptions<T>) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState<SortOrder>(initialSortOrder);

  const filteredAndSortedData = useMemo(() => {
    let filtered = data.filter((item) => {
      // Search filter
      if (searchTerm) {
        if (customSearchFunction) {
          if (!customSearchFunction(item, searchTerm)) return false;
        } else if (searchFields.length > 0) {
          const matchesSearch = searchFields.some((field) => {
            const value = item[field];
            return typeof value === "string" && 
                   value.toLowerCase().includes(searchTerm.toLowerCase());
          });
          if (!matchesSearch) return false;
        }
      }

      // Additional filters
      for (const [filterKey, filter] of Object.entries(filters)) {
        if (filter.selectedValues.length > 0) {
          const itemValue = filter.getValue(item);
          if (!itemValue || !filter.selectedValues.includes(itemValue)) {
            return false;
          }
        }
      }

      return true;
    });

    // Sorting
    if (sortOrder !== "none") {
      if (customSortFunction) {
        filtered = filtered.sort((a, b) => customSortFunction(a, b, sortOrder));
      } else if (defaultSortField) {
        filtered = filtered.sort((a, b) => {
          const aValue = a[defaultSortField];
          const bValue = b[defaultSortField];
          
          if (typeof aValue === "string" && typeof bValue === "string") {
            const comparison = aValue.toLowerCase().localeCompare(bValue.toLowerCase());
            return sortOrder === "asc" ? comparison : -comparison;
          }
          
          if (typeof aValue === "number" && typeof bValue === "number") {
            const comparison = aValue - bValue;
            return sortOrder === "asc" ? comparison : -comparison;
          }
          
          return 0;
        });
      }
    }

    return filtered;
  }, [data, searchTerm, sortOrder, defaultSortField, searchFields, filters, customSearchFunction, customSortFunction]);

  const handleSort = () => {
    if (sortOrder === "none") {
      setSortOrder("asc");
    } else if (sortOrder === "asc") {
      setSortOrder("desc");
    } else {
      setSortOrder("none");
    }
  };

  return {
    searchTerm,
    setSearchTerm,
    sortOrder,
    setSortOrder,
    handleSort,
    filteredData: filteredAndSortedData,
  };
}