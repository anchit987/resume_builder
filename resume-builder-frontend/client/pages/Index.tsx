import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, Download, CheckCircle, Loader2, AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

interface ProcessedResume {
  success: boolean;
  data?: any;
  error?: string;
}

const TARGET_ROLES = [
  "Software Engineer",
  "Data Scientist", 
  "Product Manager",
  "UX Designer",
  "DevOps Engineer",
  "Backend Developer",
  "Frontend Developer",
  "ML Engineer",
  "QA Engineer",
  "Tech Lead"
];

const LOADING_MESSAGES = [
  "Parsing your resume for key information...",
  "Optimizing content for ATS systems...",
  "Matching your profile to the selected role...",
  "Finalizing the layout and formatting...",
  "Almost done! Generating your personalized PDF..."
];

export default function Index() {
  const [file, setFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [userInput, setUserInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedResume, setProcessedResume] = useState<ProcessedResume | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [fileError, setFileError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Cycle through loading messages
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setCurrentMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isProcessing]);

  const validateFile = (file: File): string => {
    // Check file type
    if (file.type !== "application/pdf") {
      return "Only PDF files are supported.";
    }
    
    // Check file size (5MB max)
    const maxSizeInBytes = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSizeInBytes) {
      return "File size must be less than 5MB.";
    }
    
    return "";
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdfFile = droppedFiles.find(file => file.type === "application/pdf");
    
    if (pdfFile) {
      const error = validateFile(pdfFile);
      if (error) {
        setFileError(error);
        toast({
          title: "Invalid file",
          description: error,
          variant: "destructive",
        });
      } else {
        setFile(pdfFile);
        setFileError("");
      }
    } else {
      const errorMsg = "Please upload a PDF file only.";
      setFileError(errorMsg);
      toast({
        title: "Invalid file type",
        description: errorMsg,
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const error = validateFile(selectedFile);
      if (error) {
        setFileError(error);
        toast({
          title: "Invalid file",
          description: error,
          variant: "destructive",
        });
      } else {
        setFile(selectedFile);
        setFileError("");
      }
    }
  };

  const downloadPDF = async (response: Response, originalFileName: string) => {
    try {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      
      // Generate filename: resume_<original>.pdf
      const baseName = originalFileName.replace(/\.[^/.]+$/, ""); // Remove extension
      link.download = `resume_${baseName}.pdf`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast({
        title: "Success!",
        description: "Your ATS-optimized resume has been generated successfully!",
      });
    } catch (error) {
      console.error("Error downloading PDF:", error);
      toast({
        title: "Download failed",
        description: "Failed to download the PDF. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a PDF file to upload.",
        variant: "destructive",
      });
      return;
    }

    if (!targetRole) {
      toast({
        title: "Target role required",
        description: "Please select your target role.",
        variant: "destructive",
      });
      return;
    }

    // Validate custom instructions length
    if (userInput.length > 500) {
      toast({
        title: "Instructions too long",
        description: "Additional context must be 500 characters or less.",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);
    setCurrentMessageIndex(0);
    setProcessedResume(null);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("target_role", targetRole);
      formData.append("user_input", userInput);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        // Try to get error message from response
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      // Check if response is PDF (for download) or JSON (for display)
      const contentType = response.headers.get("content-type");
      
      if (contentType?.includes("application/pdf")) {
        // Handle PDF download
        await downloadPDF(response, file.name);
        setProcessedResume({ success: true });
      } else {
        // Handle JSON response (fallback)
        const result = await response.json();
        setProcessedResume({ success: true, data: result });
        
        toast({
          title: "Resume processed successfully!",
          description: "Your resume has been optimized for ATS systems.",
        });
      }
    } catch (error) {
      console.error("Error processing resume:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      
      setProcessedResume({ 
        success: false, 
        error: errorMessage
      });
      
      toast({
        title: "Processing failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setTargetRole("");
    setUserInput("");
    setProcessedResume(null);
    setFileError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const retrySubmit = () => {
    setProcessedResume(null);
    handleSubmit(new Event('submit') as any);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="gradient-purple-blue p-2 rounded-lg">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
                ATS Resume Optimizer
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12 space-y-12">
        {/* Hero Section */}
        <section className="text-center space-y-6">
          <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
            Transform Your Resume for{" "}
            <span className="bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
              ATS Success
            </span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Upload your PDF resume and get an ATS-optimized version tailored to your target role.
            Increase your chances of getting past automated screening systems.
          </p>
        </section>

        {/* Upload Form */}
        <section className="max-w-2xl mx-auto">
          <Card className="gradient-card border-border/50 p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload Area */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Upload Resume (PDF) <span className="text-destructive">*</span>
                </label>
                <div
                  className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
                    isDragOver
                      ? "border-primary bg-primary/5 scale-105"
                      : fileError 
                        ? "border-destructive bg-destructive/5"
                        : "border-border hover:border-primary/50 hover:bg-primary/5"
                  } ${file && !fileError ? "border-primary bg-primary/5" : ""}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                    required
                  />
                  
                  <div className="space-y-4">
                    {file && !fileError ? (
                      <div className="flex items-center justify-center space-x-3 text-primary">
                        <CheckCircle className="h-8 w-8" />
                        <div>
                          <p className="font-medium">{file.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                    ) : (
                      <>
                        {fileError ? (
                          <AlertTriangle className="h-12 w-12 mx-auto text-destructive" />
                        ) : (
                          <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                        )}
                        <div>
                          <p className="text-lg font-medium">
                            {fileError ? "Invalid File" : "Drop your resume here"}
                          </p>
                          <p className={fileError ? "text-destructive" : "text-muted-foreground"}>
                            {fileError || (
                              <>or <span className="text-primary underline cursor-pointer">browse files</span></>
                            )}
                          </p>
                          {!fileError && (
                            <p className="text-sm text-muted-foreground mt-2">
                              PDF format only • Max 5MB
                            </p>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Target Role Dropdown */}
              <div className="space-y-2">
                <label htmlFor="targetRole" className="text-sm font-medium text-foreground">
                  Target Role <span className="text-destructive">*</span>
                </label>
                <Select value={targetRole} onValueChange={setTargetRole} required>
                  <SelectTrigger className="bg-background/50 border-border/50 focus:border-primary">
                    <SelectValue placeholder="Select your target role" />
                  </SelectTrigger>
                  <SelectContent>
                    {TARGET_ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {role}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Custom Instructions */}
              <div className="space-y-2">
                <label htmlFor="userInput" className="text-sm font-medium text-foreground">
                  Any additional context for the resume?
                </label>
                <Textarea
                  id="userInput"
                  placeholder="Write anything specific you want AI to include or emphasize..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  className="min-h-[100px] resize-none bg-background/50 border-border/50 focus:border-primary"
                  maxLength={500}
                />
                <p className="text-xs text-muted-foreground">
                  {userInput.length}/500 characters
                </p>
              </div>

              {/* Submit Button */}
              <div className="flex space-x-4">
                <Button
                  type="submit"
                  disabled={!file || !targetRole || isProcessing || !!fileError}
                  className="flex-1 gradient-purple-blue hover:scale-105 transition-all duration-300 text-white border-0"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <FileText className="mr-2 h-4 w-4" />
                      Generate ATS-Friendly Resume
                    </>
                  )}
                </Button>
                
                {(file || processedResume) && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={resetForm}
                    className="hover:scale-105 transition-all duration-300"
                    disabled={isProcessing}
                  >
                    Reset
                  </Button>
                )}
              </div>
            </form>
          </Card>
        </section>

        {/* Loading State */}
        {isProcessing && (
          <section className="max-w-2xl mx-auto">
            <Card className="gradient-card border-border/50 p-8">
              <div className="text-center space-y-6">
                <div className="flex justify-center">
                  <div className="relative">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <div className="absolute inset-0 h-12 w-12 rounded-full border-2 border-primary/20"></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold">Processing Your Resume</h3>
                  <p className="text-muted-foreground animate-pulse">
                    {LOADING_MESSAGES[currentMessageIndex]}
                  </p>
                </div>
              </div>
            </Card>
          </section>
        )}

        {/* Results Section */}
        {processedResume && !isProcessing && (
          <section className="max-w-4xl mx-auto">
            <Card className="gradient-card border-border/50 p-8">
              <div className="space-y-6">
                {processedResume.success ? (
                  <div className="text-center space-y-4">
                    <div className="flex justify-center">
                      <CheckCircle className="h-16 w-16 text-green-500" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-green-500">Success!</h3>
                      <p className="text-muted-foreground">
                        Your ATS-optimized resume has been generated and downloaded successfully!
                      </p>
                    </div>
                    <Button
                      onClick={resetForm}
                      variant="outline"
                      className="hover:scale-105 transition-all duration-300"
                    >
                      Process Another Resume
                    </Button>
                  </div>
                ) : (
                  <div className="text-center space-y-4">
                    <div className="flex justify-center">
                      <AlertTriangle className="h-16 w-16 text-destructive" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-destructive">Processing Failed</h3>
                      <p className="text-muted-foreground mb-4">
                        {processedResume.error || "An unexpected error occurred"}
                      </p>
                    </div>
                    <div className="flex justify-center space-x-4">
                      <Button
                        onClick={retrySubmit}
                        className="gradient-purple-blue hover:scale-105 transition-all duration-300 text-white border-0"
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Try Again
                      </Button>
                      <Button
                        onClick={resetForm}
                        variant="outline"
                        className="hover:scale-105 transition-all duration-300"
                      >
                        Start Over
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 mt-24">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-muted-foreground text-sm">
              © 2024 ATS Resume Optimizer. All rights reserved.
            </p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Privacy
              </a>
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Terms
              </a>
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Support
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
