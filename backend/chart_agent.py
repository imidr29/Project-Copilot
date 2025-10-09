import logging
import matplotlib.pyplot as plt
import matplotlib
import base64
import io
from typing import Dict, Any, List, Optional
import numpy as np

# Set matplotlib to use non-interactive backend
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

class ChartAgent:
    """
    Agent for generating matplotlib charts and ECharts JSON specifications from query results
    """
    
    def generate_chart_image(self, query: str, data: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate matplotlib chart and return as base64 encoded image
        """
        if not data or len(data) == 0:
            logger.info("No data provided for chart generation")
            return None
        
        try:
            query_lower = query.lower()
            
            # Determine chart type based on query
            if "pie" in query_lower or "%" in query or "percentage" in query_lower:
                return self._create_pie_chart_image(data, query)
            elif "trend" in query_lower or "over time" in query_lower or "daily" in query_lower:
                return self._create_line_chart_image(data, query)
            elif "pareto" in query_lower or "top" in query_lower:
                return self._create_pareto_chart_image(data, query)
            elif "stacked" in query_lower:
                return self._create_stacked_bar_chart_image(data, query)
            elif "heatmap" in query_lower:
                return self._create_heatmap_image(data, query)
            else:
                # Default: choose based on data structure
                return self._auto_select_chart_image(data, query)
                
        except Exception as e:
            logger.error(f"Error generating chart image: {e}")
            return None
    
    def generate_chart_spec(self, query: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generate ECharts specification based on query and data
        """
        if not data or len(data) == 0:
            logger.info("No data provided for chart generation")
            return None
        
        try:
            query_lower = query.lower()
            
            # Determine chart type based on query
            if "pie" in query_lower or "%" in query or "percentage" in query_lower:
                result = self._generate_pie_chart(data)
            elif "trend" in query_lower or "over time" in query_lower or "daily" in query_lower:
                result = self._generate_line_chart(data)
            elif "bucket" in query_lower or "distribution" in query_lower or "histogram" in query_lower:
                result = self._generate_bar_chart(data)
            elif "stacked" in query_lower:
                result = self._generate_stacked_bar_chart(data)
            elif "heatmap" in query_lower:
                result = self._generate_heatmap(data)
            elif "pareto" in query_lower or "top" in query_lower:
                result = self._generate_pareto_chart(data)
            elif "compare" in query_lower:
                result = self._generate_comparison_chart(data)
            else:
                # Default: choose based on data structure
                result = self._auto_select_chart(data)
            
            if result:
                logger.info(f"Successfully generated {result.get('type', 'unknown')} chart")
            else:
                logger.warning("Chart generation returned None")
                
            return result
            
        except Exception as e:
            logger.error(f"Error generating chart spec: {e}")
            return None
    
    def _generate_pie_chart(self, data: List[Dict]) -> Dict:
        """Generate pie chart specification"""
        if not data or len(data) == 0:
            logger.warning("No data for pie chart")
            return None
            
        try:
            # Find label and value columns
            keys = list(data[0].keys())
            label_col = keys[0]
            value_col = None
            
            # Look for numeric columns
            for key in keys:
                if any(term in key.lower() for term in ['count', 'total', 'sum', 'amount', 'value', 'number']):
                    # Check if this column has numeric data
                    try:
                        sample_val = data[0].get(key)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            value_col = key
                            break
                    except:
                        continue
            
            # If no numeric column found, use the second column or first column
            if not value_col:
                value_col = keys[1] if len(keys) > 1 else keys[0]
            
            logger.info(f"Pie chart - Label column: {label_col}, Value column: {value_col}")
            
            chart_data = []
            for row in data:
                try:
                    # Handle null values
                    label = str(row[label_col]) if row[label_col] is not None else "Unknown"
                    
                    # Convert value to float
                    raw_value = row[value_col]
                    if raw_value is None:
                        value = 0.0
                    else:
                        value = float(raw_value)
                    
                    # Only add if value is greater than 0
                    if value > 0:
                        chart_data.append({"value": value, "name": label})
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing row for pie chart: {row}, error: {e}")
                    continue
            
            if not chart_data:
                logger.warning("No valid data for pie chart")
                return None
            
            logger.info(f"Pie chart data: {chart_data}")
            
            return {
                "title": {"text": "Distribution", "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                "legend": {"orient": "vertical", "left": "left"},
                "series": [{
                    "name": "Data",
                    "type": "pie",
                    "radius": "50%",
                    "data": chart_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }]
            }
        except Exception as e:
            logger.error(f"Error generating pie chart: {e}")
            return None
    
    def _generate_line_chart(self, data: List[Dict]) -> Dict:
        """Generate line chart specification"""
        keys = list(data[0].keys())
        
        # X-axis (usually date or time)
        x_col = None
        for key in keys:
            if any(term in key.lower() for term in ['date', 'time', 'day']):
                x_col = key
                break
        if not x_col:
            x_col = keys[0]
        
        # Y-axis (numeric values)
        y_cols = [k for k in keys if k != x_col and isinstance(data[0].get(k), (int, float))]
        
        x_data = [str(row[x_col]) for row in data]
        series = []
        
        for y_col in y_cols:
            series.append({
                "name": y_col.replace('_', ' ').title(),
                "type": "line",
                "data": [float(row[y_col]) if row[y_col] is not None else 0 for row in data],
                "smooth": True
            })
        
        return {
            "type": "line",
            "title": {"text": "Trend Over Time", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [s["name"] for s in series], "top": "bottom"},
            "xAxis": {"type": "category", "data": x_data, "name": x_col},
            "yAxis": {"type": "value"},
            "series": series
        }
    
    def _generate_bar_chart(self, data: List[Dict]) -> Dict:
        """Generate bar chart specification"""
        if not data or len(data) == 0:
            logger.warning("No data for bar chart")
            return None
            
        try:
            keys = list(data[0].keys())
            
            # Category axis
            category_col = keys[0]
            
            # Find numeric value columns
            value_cols = []
            for k in keys:
                if k != category_col:
                    try:
                        sample_val = data[0].get(k)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            value_cols.append(k)
                    except:
                        continue
            
            # If no numeric columns found, use the second column
            if not value_cols and len(keys) > 1:
                value_cols = [keys[1]]
            
            if not value_cols:
                logger.warning("No numeric columns found for bar chart")
                return None
            
            categories = [str(row[category_col]) if row[category_col] is not None else "Unknown" for row in data]
            series = []
            
            for val_col in value_cols:
                series_data = []
                for row in data:
                    try:
                        val = row[val_col]
                        if val is None:
                            series_data.append(0)
                        else:
                            series_data.append(float(val))
                    except (ValueError, TypeError):
                        series_data.append(0)
                
                series.append({
                    "name": val_col.replace('_', ' ').title(),
                    "type": "bar",
                    "data": series_data
                })
            
            logger.info(f"Bar chart - Categories: {len(categories)}, Series: {len(series)}")
            
            return {
                "title": {"text": "Comparison", "left": "center"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": [s["name"] for s in series], "top": "bottom"},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": series
            }
        except Exception as e:
            logger.error(f"Error generating bar chart: {e}")
            return None
    
    def _generate_stacked_bar_chart(self, data: List[Dict]) -> Dict:
        """Generate stacked bar chart specification"""
        keys = list(data[0].keys())
        
        # Category axis
        category_col = keys[0]
        
        # Value columns
        value_cols = [k for k in keys if k != category_col and isinstance(data[0].get(k), (int, float))]
        
        categories = [str(row[category_col]) for row in data]
        series = []
        
        for val_col in value_cols:
            series.append({
                "name": val_col.replace('_', ' ').title(),
                "type": "bar",
                "stack": "total",
                "data": [float(row[val_col]) if row[val_col] is not None else 0 for row in data]
            })
        
        return {
            "type": "bar",
            "title": {"text": "Stacked Comparison", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"data": [s["name"] for s in series], "top": "bottom"},
            "xAxis": {"type": "category", "data": categories},
            "yAxis": {"type": "value"},
            "series": series
        }
    
    def _generate_heatmap(self, data: List[Dict]) -> Dict:
        """Generate heatmap specification"""
        keys = list(data[0].keys())
        
        if len(keys) < 3:
            return self._generate_bar_chart(data)
        
        x_col, y_col, value_col = keys[0], keys[1], keys[2]
        
        x_values = sorted(list(set(str(row[x_col]) for row in data)))
        y_values = sorted(list(set(str(row[y_col]) for row in data)))
        
        heatmap_data = []
        for row in data:
            x_idx = x_values.index(str(row[x_col]))
            y_idx = y_values.index(str(row[y_col]))
            value = float(row[value_col]) if row[value_col] else 0
            heatmap_data.append([x_idx, y_idx, value])
        
        return {
            "type": "heatmap",
            "title": {"text": "Heatmap", "left": "center"},
            "tooltip": {"position": "top"},
            "grid": {"height": "50%", "top": "10%"},
            "xAxis": {"type": "category", "data": x_values, "splitArea": {"show": True}},
            "yAxis": {"type": "category", "data": y_values, "splitArea": {"show": True}},
            "visualMap": {
                "min": 0,
                "max": max([d[2] for d in heatmap_data]) if heatmap_data else 100,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "0%"
            },
            "series": [{
                "name": "Value",
                "type": "heatmap",
                "data": heatmap_data,
                "label": {"show": True},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }
    
    '''def _generate_pareto_chart(self, data: List[Dict]) -> Dict:
        """Generate Pareto chart (bar + line)"""
        keys = list(data[0].keys())
        
        category_col = keys[0]
        value_col = keys[1] if len(keys) > 1 else keys[0]
        
        # Sort by value descending
        sorted_data = sorted(data, key=lambda x: float(x[value_col]) if x[value_col] else 0, reverse=True)
        
        categories = [str(row[category_col]) for row in sorted_data]
        values = [float(row[value_col]) if row[value_col] else 0 for row in sorted_data]
        
        # Calculate cumulative percentage
        total = sum(values)
        cumulative = []
        cum_sum = 0
        for val in values:
            cum_sum += val
            cumulative.append(round((cum_sum / total) * 100, 1) if total > 0 else 0)
        
        return {
            "type": "bar",
            "title": {"text": "Pareto Analysis", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"data": ["Count", "Cumulative %"], "top": "bottom"},
            "xAxis": [{"type": "category", "data": categories, "axisPointer": {"type": "shadow"}}],
            "yAxis": [
                {"type": "value", "name": "Count", "position": "left"},
                {"type": "value", "name": "Cumulative %", "position": "right", "max": 100}
            ],
            "series": [
                {
                    "name": "Count",
                    "type": "bar",
                    "data": values,
                    "itemStyle": {"color": "#5470c6"}
                },
                {
                    "name": "Cumulative %",
                    "type": "line",
                    "yAxisIndex": 1,
                    "data": cumulative,
                    "itemStyle": {"color": "#ee6666"},
                    "lineStyle": {"width": 2}
                }
            ]
        }'''
    def _generate_pareto_chart(self, data: List[Dict]) -> Dict:
        if not data:
            logger.info("No data for pareto chart")
            return None
        keys = list(data[0].keys())
        category_col = keys[0]
        value_col = keys[1] if len(keys) > 1 else keys[0]
        # Check if value_col is numeric
        if not all(isinstance(row.get(value_col), (int, float)) for row in data):
            logger.error("Value column is not numeric")
            return None
        sorted_data = sorted(data, key=lambda x: float(x[value_col]) if x[value_col] else 0, reverse=True)
        categories = [str(row[category_col]) for row in sorted_data]
        values = [float(row[value_col]) if row[value_col] else 0 for row in sorted_data]
        total = sum(values)
        cumulative = []
        cum_sum = 0
        for val in values:
            cum_sum += val
            cumulative.append(round((cum_sum / total) * 100, 1) if total > 0 else 0)
        logger.info("Pareto chart generated")
        return {
            "type": "bar",
            "title": {"text": "Pareto Analysis", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"data": ["Count", "Cumulative %"], "top": "bottom"},
            "xAxis": [{"type": "category", "data": categories, "axisPointer": {"type": "shadow"}}],
            "yAxis": [
                {"type": "value", "name": "Count", "position": "left"},
                {"type": "value", "name": "Cumulative %", "position": "right", "max": 100}
            ],
            "series": [
                {"name": "Count", "type": "bar", "data": values, "itemStyle": {"color": "#5470c6"}},
                {"name": "Cumulative %", "type": "line", "yAxisIndex": 1, "data": cumulative, "itemStyle": {"color": "#ee6666"}, "lineStyle": {"width": 2}}
            ]
        }
    
    def _generate_comparison_chart(self, data: List[Dict]) -> Dict:
        """Generate comparison chart (grouped bar)"""
        return self._generate_bar_chart(data)
    
    def _auto_select_chart(self, data: List[Dict]) -> Dict:
        """Auto-select chart type based on data structure"""
        if not data or len(data) == 0:
            return None
            
        try:
            keys = list(data[0].keys())
            num_rows = len(data)
            
            logger.info(f"Auto-selecting chart for {num_rows} rows with keys: {keys}")
            
            # If only 2-5 rows with percentage/total, use pie
            if num_rows <= 5 and any('percent' in k.lower() or 'total' in k.lower() or 'count' in k.lower() for k in keys):
                result = self._generate_pie_chart(data)
                if result:
                    return result
            
            # If date/time column exists, use line chart
            if any('date' in k.lower() or 'time' in k.lower() for k in keys):
                result = self._generate_line_chart(data)
                if result:
                    return result
            
            # Try bar chart
            result = self._generate_bar_chart(data)
            if result:
                return result
            
            # Fallback: simple bar chart with first two columns
            return self._generate_fallback_chart(data)
            
        except Exception as e:
            logger.error(f"Error in auto-select chart: {e}")
            return self._generate_fallback_chart(data)
    
    def _generate_fallback_chart(self, data: List[Dict]) -> Dict:
        """Generate a simple fallback chart when other methods fail"""
        try:
            if not data or len(data) == 0:
                return None
                
            keys = list(data[0].keys())
            if len(keys) < 2:
                return None
            
            # Use first column as category, second as value
            category_col = keys[0]
            value_col = keys[1]
            
            categories = []
            values = []
            
            for row in data:
                try:
                    cat = str(row[category_col]) if row[category_col] is not None else "Unknown"
                    val = float(row[value_col]) if row[value_col] is not None else 0.0
                    categories.append(cat)
                    values.append(val)
                except:
                    continue
            
            if not categories:
                return None
            
            logger.info(f"Fallback chart generated with {len(categories)} categories")
            
            return {
                "title": {"text": "Data Visualization", "left": "center"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": [{
                    "name": value_col.replace('_', ' ').title(),
                    "type": "bar",
                    "data": values
                }]
            }
        except Exception as e:
            logger.error(f"Error generating fallback chart: {e}")
            return None
    
    # Matplotlib Chart Generation Methods
    
    def _create_pie_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create pie chart using matplotlib"""
        try:
            if not data:
                return None
            
            # Find label and value columns
            keys = list(data[0].keys())
            label_col = keys[0]
            value_col = None
            
            # Look for numeric columns
            for key in keys:
                if any(term in key.lower() for term in ['count', 'total', 'sum', 'amount', 'value', 'number']):
                    try:
                        sample_val = data[0].get(key)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            value_col = key
                            break
                    except:
                        continue
            
            if not value_col:
                value_col = keys[1] if len(keys) > 1 else keys[0]
            
            # Prepare data
            labels = []
            values = []
            for row in data:
                try:
                    label = str(row[label_col]) if row[label_col] is not None else "Unknown"
                    raw_value = row[value_col]
                    if raw_value is not None:
                        value = float(raw_value)
                        if value > 0:
                            labels.append(label)
                            values.append(value)
                except:
                    continue
            
            if not values:
                return None
            
            # Create chart
            plt.figure(figsize=(10, 8))
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            wedges, texts, autotexts = plt.pie(values, labels=labels, autopct='%1.1f%%', 
                                              colors=colors, startangle=90)
            
            # Customize
            plt.title(f'Distribution - {query[:50]}...', fontsize=14, fontweight='bold')
            plt.axis('equal')
            
            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating pie chart image: {e}")
            return None
    
    def _create_line_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create line chart using matplotlib"""
        try:
            if not data:
                return None
            
            keys = list(data[0].keys())
            
            # X-axis (usually date or time)
            x_col = None
            for key in keys:
                if any(term in key.lower() for term in ['date', 'time', 'day']):
                    x_col = key
                    break
            if not x_col:
                x_col = keys[0]
            
            # Y-axis (numeric values)
            y_cols = []
            for k in keys:
                if k != x_col:
                    try:
                        sample_val = data[0].get(k)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            y_cols.append(k)
                    except:
                        continue
            
            if not y_cols:
                return None
            
            # Create chart
            plt.figure(figsize=(12, 8))
            
            x_data = [str(row[x_col]) for row in data]
            
            for y_col in y_cols:
                y_data = []
                for row in data:
                    try:
                        val = row[y_col]
                        y_data.append(float(val) if val is not None else 0)
                    except:
                        y_data.append(0)
                
                plt.plot(x_data, y_data, marker='o', linewidth=2, label=y_col.replace('_', ' ').title())
            
            plt.title(f'Trend Analysis - {query[:50]}...', fontsize=14, fontweight='bold')
            plt.xlabel(x_col.replace('_', ' ').title())
            plt.ylabel('Value')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating line chart image: {e}")
            return None
    
    def _create_pareto_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create Pareto chart using matplotlib"""
        try:
            if not data:
                return None
            
            keys = list(data[0].keys())
            category_col = keys[0]
            value_col = keys[1] if len(keys) > 1 else keys[0]
            
            # Sort by value descending
            sorted_data = sorted(data, key=lambda x: float(x[value_col]) if x[value_col] else 0, reverse=True)
            
            categories = [str(row[category_col]) if row[category_col] is not None else "Unknown" for row in sorted_data]
            values = [float(row[value_col]) if row[value_col] else 0 for row in sorted_data]
            
            # Calculate cumulative percentage
            total = sum(values)
            cumulative = []
            cum_sum = 0
            for val in values:
                cum_sum += val
                cumulative.append((cum_sum / total) * 100 if total > 0 else 0)
            
            # Create chart
            fig, ax1 = plt.subplots(figsize=(12, 8))
            
            # Bar chart
            bars = ax1.bar(range(len(categories)), values, color='skyblue', alpha=0.7)
            ax1.set_xlabel('Categories')
            ax1.set_ylabel('Count', color='blue')
            ax1.set_title(f'Pareto Analysis - {query[:50]}...', fontsize=14, fontweight='bold')
            ax1.set_xticks(range(len(categories)))
            ax1.set_xticklabels(categories, rotation=45, ha='right')
            
            # Line chart for cumulative percentage
            ax2 = ax1.twinx()
            ax2.plot(range(len(categories)), cumulative, color='red', marker='o', linewidth=2, markersize=6)
            ax2.set_ylabel('Cumulative Percentage (%)', color='red')
            ax2.set_ylim(0, 100)
            
            # Add percentage labels on line
            for i, (x, y) in enumerate(zip(range(len(categories)), cumulative)):
                ax2.annotate(f'{y:.1f}%', (x, y), textcoords="offset points", xytext=(0,10), ha='center')
            
            plt.tight_layout()
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating pareto chart image: {e}")
            return None
    
    def _create_stacked_bar_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create stacked bar chart using matplotlib"""
        try:
            if not data:
                return None
            
            keys = list(data[0].keys())
            category_col = keys[0]
            
            # Find numeric value columns
            value_cols = []
            for k in keys:
                if k != category_col:
                    try:
                        sample_val = data[0].get(k)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            value_cols.append(k)
                    except:
                        continue
            
            if not value_cols:
                return None
            
            categories = [str(row[category_col]) if row[category_col] is not None else "Unknown" for row in data]
            
            # Create chart
            plt.figure(figsize=(12, 8))
            
            bottom = np.zeros(len(categories))
            colors = plt.cm.Set3(np.linspace(0, 1, len(value_cols)))
            
            for i, val_col in enumerate(value_cols):
                values = []
                for row in data:
                    try:
                        val = row[val_col]
                        values.append(float(val) if val is not None else 0)
                    except:
                        values.append(0)
                
                plt.bar(categories, values, bottom=bottom, label=val_col.replace('_', ' ').title(), 
                       color=colors[i], alpha=0.8)
                bottom += values
            
            plt.title(f'Stacked Comparison - {query[:50]}...', fontsize=14, fontweight='bold')
            plt.xlabel(category_col.replace('_', ' ').title())
            plt.ylabel('Value')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating stacked bar chart image: {e}")
            return None
    
    def _create_heatmap_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create heatmap using matplotlib"""
        try:
            if not data or len(data) == 0:
                return None
            
            keys = list(data[0].keys())
            if len(keys) < 3:
                return self._create_bar_chart_image(data, query)
            
            x_col, y_col, value_col = keys[0], keys[1], keys[2]
            
            # Get unique values
            x_values = sorted(list(set(str(row[x_col]) for row in data)))
            y_values = sorted(list(set(str(row[y_col]) for row in data)))
            
            # Create matrix
            matrix = np.zeros((len(y_values), len(x_values)))
            
            for row in data:
                try:
                    x_idx = x_values.index(str(row[x_col]))
                    y_idx = y_values.index(str(row[y_col]))
                    value = float(row[value_col]) if row[value_col] else 0
                    matrix[y_idx, x_idx] = value
                except:
                    continue
            
            # Create chart
            plt.figure(figsize=(12, 8))
            im = plt.imshow(matrix, cmap='YlOrRd', aspect='auto')
            
            # Set ticks
            plt.xticks(range(len(x_values)), x_values, rotation=45)
            plt.yticks(range(len(y_values)), y_values)
            
            # Add colorbar
            plt.colorbar(im, label='Value')
            
            # Add text annotations
            for i in range(len(y_values)):
                for j in range(len(x_values)):
                    text = plt.text(j, i, f'{matrix[i, j]:.1f}', ha="center", va="center", color="black")
            
            plt.title(f'Heatmap - {query[:50]}...', fontsize=14, fontweight='bold')
            plt.xlabel(x_col.replace('_', ' ').title())
            plt.ylabel(y_col.replace('_', ' ').title())
            plt.tight_layout()
            
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating heatmap image: {e}")
            return None
    
    def _create_bar_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Create bar chart using matplotlib"""
        try:
            if not data:
                return None
            
            keys = list(data[0].keys())
            category_col = keys[0]
            
            # Find numeric value columns
            value_cols = []
            for k in keys:
                if k != category_col:
                    try:
                        sample_val = data[0].get(k)
                        if sample_val is not None and (isinstance(sample_val, (int, float)) or str(sample_val).replace('.', '').replace('-', '').isdigit()):
                            value_cols.append(k)
                    except:
                        continue
            
            if not value_cols:
                return None
            
            categories = [str(row[category_col]) if row[category_col] is not None else "Unknown" for row in data]
            
            # Create chart
            plt.figure(figsize=(12, 8))
            
            x = np.arange(len(categories))
            width = 0.35
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(value_cols)))
            
            for i, val_col in enumerate(value_cols):
                values = []
                for row in data:
                    try:
                        val = row[val_col]
                        values.append(float(val) if val is not None else 0)
                    except:
                        values.append(0)
                
                plt.bar(x + i * width, values, width, label=val_col.replace('_', ' ').title(), 
                       color=colors[i], alpha=0.8)
            
            plt.title(f'Comparison - {query[:50]}...', fontsize=14, fontweight='bold')
            plt.xlabel(category_col.replace('_', ' ').title())
            plt.ylabel('Value')
            plt.xticks(x + width/2, categories, rotation=45)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            return self._save_chart_as_base64()
            
        except Exception as e:
            logger.error(f"Error creating bar chart image: {e}")
            return None
    
    def _auto_select_chart_image(self, data: List[Dict], query: str) -> Optional[str]:
        """Auto-select chart type based on data structure"""
        try:
            if not data:
                return None
            
            keys = list(data[0].keys())
            num_rows = len(data)
            
            # If only 2-5 rows with percentage/total, use pie
            if num_rows <= 5 and any('percent' in k.lower() or 'total' in k.lower() or 'count' in k.lower() for k in keys):
                result = self._create_pie_chart_image(data, query)
                if result:
                    return result
            
            # If date/time column exists, use line chart
            if any('date' in k.lower() or 'time' in k.lower() for k in keys):
                result = self._create_line_chart_image(data, query)
                if result:
                    return result
            
            # Default to bar chart
            return self._create_bar_chart_image(data, query)
            
        except Exception as e:
            logger.error(f"Error in auto-select chart image: {e}")
            return self._create_bar_chart_image(data, query)
    
    def _save_chart_as_base64(self) -> str:
        """Save current matplotlib figure as base64 encoded image"""
        try:
            # Save to bytes buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Clear the figure
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Error saving chart as base64: {e}")
            plt.close()
            return None