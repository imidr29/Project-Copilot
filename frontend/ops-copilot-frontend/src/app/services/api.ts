import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, BehaviorSubject, of } from 'rxjs';
import { catchError, retry, timeout, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface QueryRequest {
  query: string;
  conversation_history?: Array<{role: string, content: string}>;
}

export interface QueryResponse {
  query: string;
  sql_query: string;
  results: any[];
  chart_spec?: any;
  natural_language_response: string;
  metadata: {
    result_count: number;
    execution_time_ms: number;
    chart_type?: string;
  };
}

export interface Suggestion {
  suggestions: string[];
}

export interface SchemaResponse {
  schema: any;
}

export interface HealthResponse {
  status: string;
  database: string;
  langchain: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000';
  private connectionStatus = new BehaviorSubject<boolean>(false);
  public connectionStatus$ = this.connectionStatus.asObservable();

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }),
    timeout: 60000 // 60 seconds timeout for LLM/Pinecone operations
  };

  constructor(private http: HttpClient) {
    this.checkHealth();
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      // Server-side error
      if (error.status === 0) {
        errorMessage = 'Network connection failed. Please check your internet connection and ensure the backend server is running.';
      } else if (error.status === 500) {
        errorMessage = 'Server error occurred. This might be due to LLM processing issues or Pinecone vector search problems. Please try again.';
      } else if (error.status === 503) {
        errorMessage = 'Service temporarily unavailable. The database or LLM service might be down. Please try again later.';
      } else if (error.status === 408 || (error as any).name === 'TimeoutError') {
        errorMessage = 'Request timeout. The LLM or Pinecone operations are taking longer than expected. Please try a simpler query or wait a bit longer.';
      } else {
        errorMessage = `Server Error: ${error.status} - ${error.message}`;
        if (error.error && error.error.detail) {
          errorMessage = error.error.detail;
        }
      }
    }
    
    console.error('API Error:', errorMessage, error);
    this.connectionStatus.next(false);
    return throwError(() => new Error(errorMessage));
  }

  private checkHealth(): void {
    this.getHealth().subscribe({
      next: () => this.connectionStatus.next(true),
      error: () => this.connectionStatus.next(false)
    });
  }

  processQuery(request: QueryRequest): Observable<QueryResponse> {
    console.log('Sending query request:', request);
    return this.http.post<QueryResponse>(`${this.baseUrl}/api/query`, request, this.httpOptions)
      .pipe(
        retry(2), // Increased retries for LLM operations
        timeout(60000), // Increased timeout for LLM/Pinecone operations
        catchError(this.handleError.bind(this))
      );
  }

  getSuggestions(): Observable<Suggestion> {
    return this.http.get<Suggestion>(`${this.baseUrl}/api/suggestions`, this.httpOptions)
      .pipe(
        retry(1),
        catchError(this.handleError.bind(this))
      );
  }

  getSchema(): Observable<SchemaResponse> {
    return this.http.get<SchemaResponse>(`${this.baseUrl}/api/schema`, this.httpOptions)
      .pipe(
        retry(1),
        catchError(this.handleError.bind(this))
      );
  }

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`, this.httpOptions)
      .pipe(
        timeout(5000),
        catchError(this.handleError.bind(this))
      );
  }

  // Method to test connection and update status
  testConnection(): Observable<boolean> {
    return new Observable(observer => {
      this.getHealth().subscribe({
        next: (response) => {
          this.connectionStatus.next(true);
          observer.next(true);
          observer.complete();
        },
        error: (error) => {
          this.connectionStatus.next(false);
          observer.next(false);
          observer.complete();
        }
      });
    });
  }

  // Get query suggestions for better UX
  getQuerySuggestions(): Observable<string[]> {
    return this.getSuggestions().pipe(
      map(response => response.suggestions),
      catchError(() => {
        // Fallback suggestions if API fails
        return of([
          "What % of time was the machine ACTIVE vs INACTIVE today?",
          "Show me all INACTIVE episodes less than 60 seconds",
          "Top 5 reasons contributing to INACTIVE time",
          "Trend of daily total INACTIVE minutes over last 14 days",
          "Calculate approximate MTTR for last week"
        ]);
      })
    );
  }
}