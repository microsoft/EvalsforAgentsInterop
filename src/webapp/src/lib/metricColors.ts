import { RubricType } from './types';

export const getMetricColor = (metric: RubricType): string => {
  switch (metric) {
    case 'groundedness':
      return 'text-blue-600';
    case 'toolEfficiency':
      return 'text-purple-600';
    case 'accuracy':
      return 'text-green-600';
    case 'relevance':
      return 'text-yellow-600';
    case 'overall':
      return 'text-primary';
    default:
      return 'text-foreground';
  }
};

export const getMetricBgColor = (metric: RubricType): string => {
  switch (metric) {
    case 'groundedness':
      return 'bg-blue-100 border-blue-300';
    case 'toolEfficiency':
      return 'bg-purple-100 border-purple-300';
    case 'accuracy':
      return 'bg-green-100 border-green-300';
    case 'relevance':
      return 'bg-yellow-100 border-yellow-300';
    case 'overall':
      return 'bg-primary/10 border-primary/30';
    default:
      return 'bg-muted border-border';
  }
};

export const getMetricBadgeClass = (metric: RubricType): string => {
  switch (metric) {
    case 'groundedness':
      return 'bg-blue-100 text-blue-700 border-blue-300';
    case 'toolEfficiency':
      return 'bg-purple-100 text-purple-700 border-purple-300';
    case 'accuracy':
      return 'bg-green-100 text-green-700 border-green-300';
    case 'relevance':
      return 'bg-yellow-100 text-yellow-700 border-yellow-300';
    case 'overall':
      return 'bg-primary/10 text-primary border-primary/30';
    default:
      return '';
  }
};
