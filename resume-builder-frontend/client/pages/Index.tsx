import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, Download, CheckCircle, Loader2, AlertTriangle, RotateCcw, Sparkles } from "lucide-react";
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
  "Analyzing your resume content...",
  "Optimizing for ATS systems...",
  "Tailoring to your target role...",
  "Improving formatting and keywords...",
  "Generating your enhanced PDF..."
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
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [isProcessing]);

  const validateFile = (file: File): string => {
    if (file.type !== "application/pdf") {
      return "Only PDF files are supported.";
    }
    
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
      
      const baseName = originalFileName.replace(/\.[^/.]+$/, "");
      link.download = `resume_${baseName}_optimized.pdf`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast({
        title: "Success!",
        description: "Your ATS-optimized resume has been downloaded successfully!",
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

      const response = await fetch("${import.meta.env.VITE_API_URL}/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const contentType = response.headers.get("content-type");
      
      if (contentType?.includes("application/pdf")) {
        await downloadPDF(response, file.name);
        setProcessedResume({ success: true });
      } else {
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
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/20 bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-3 sm:py-4">
          <div className="flex items-center justify-center sm:justify-start">
            <div className="flex items-center space-x-3">
              <div className="gradient-purple-blue p-2 rounded-xl">
                <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </div>
              <h1 className="text-lg sm:text-xl md:text-2xl font-bold bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
                Resume Optimizer
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 sm:py-8 md:py-12">
        {/* Hero Section */}
        <section className="text-center space-y-4 sm:space-y-6 mb-8 sm:mb-12">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight leading-tight">
            Beat ATS Systems with{" "}
            <span className="bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
              AI-Powered
            </span>{" "}
            Optimization
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto px-4">
            Upload your resume and get an ATS-optimized version that passes automated screening systems.
          </p>
        </section>

        {/* Upload Form */}
        <section className="max-w-2xl mx-auto">
          <Card className="border border-border/30 shadow-lg backdrop-blur-sm bg-card/50 p-4 sm:p-6 md:p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload Area */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground block">
                  Upload Resume (PDF) <span className="text-destructive">*</span>
                </label>
                <div
                  className={`relative border-2 border-dashed rounded-xl p-4 sm:p-6 md:p-8 text-center transition-all duration-300 cursor-pointer ${
                    isDragOver
                      ? "border-primary bg-primary/10 scale-[1.02]"
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
                  
                  <div className="space-y-3 sm:space-y-4">
                    {file && !fileError ? (
                      <div className="flex flex-col sm:flex-row items-center justify-center sm:space-x-3 text-primary">
                        <CheckCircle className="h-8 w-8 mb-2 sm:mb-0" />
                        <div className="text-center sm:text-left">
                          <p className="font-medium text-sm sm:text-base break-all">{file.name}</p>
                          <p className="text-xs sm:text-sm text-muted-foreground">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                    ) : (
                      <>
                        {fileError ? (
                          <AlertTriangle className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-destructive" />
                        ) : (
                          <Upload className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground" />
                        )}
                        <div>
                          <p className="text-base sm:text-lg font-medium">
                            {fileError ? "Invalid File" : "Drop your resume here"}
                          </p>
                          <p className={`text-sm ${fileError ? "text-destructive" : "text-muted-foreground"}`}>
                            {fileError || (
                              <>or <span className="text-primary underline">browse files</span></>
                            )}
                          </p>
                          {!fileError && (
                            <p className="text-xs sm:text-sm text-muted-foreground mt-2">
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
                <label htmlFor="targetRole" className="text-sm font-medium text-foreground block">
                  Target Role <span className="text-destructive">*</span>
                </label>
                <Select value={targetRole} onValueChange={setTargetRole} required>
                  <SelectTrigger className="bg-background/50 border-border/50 focus:border-primary h-12">
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
                <label htmlFor="userInput" className="text-sm font-medium text-foreground block">
                  Additional Context (Optional)
                </label>
                <Textarea
                  id="userInput"
                  placeholder="Any specific skills, achievements, or keywords you want emphasized..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  className="min-h-[80px] sm:min-h-[100px] resize-none bg-background/50 border-border/50 focus:border-primary"
                  maxLength={500}
                />
                <p className="text-xs text-muted-foreground text-right">
                  {userInput.length}/500
                </p>
              </div>

              {/* Submit Button */}
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                <Button
                  type="submit"
                  disabled={!file || !targetRole || isProcessing || !!fileError}
                  className="flex-1 gradient-purple-blue hover:scale-[1.02] transition-all duration-300 text-white border-0 h-12 sm:h-11"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Optimize Resume
                    </>
                  )}
                </Button>
                
                {(file || processedResume) && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={resetForm}
                    className="hover:scale-[1.02] transition-all duration-300 h-12 sm:h-11"
                    disabled={isProcessing}
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Reset
                  </Button>
                )}
              </div>
            </form>
          </Card>
        </section>

        {/* Loading State */}
        {isProcessing && (
          <section className="max-w-2xl mx-auto mt-8">
            <Card className="border border-border/30 shadow-lg backdrop-blur-sm bg-card/50 p-6 sm:p-8">
              <div className="text-center space-y-6">
                <div className="flex justify-center">
                  <div className="relative">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <div className="absolute inset-0 h-12 w-12 rounded-full border-2 border-primary/20 animate-pulse"></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg sm:text-xl font-semibold">Processing Your Resume</h3>
                  <p className="text-sm sm:text-base text-muted-foreground animate-pulse">
                    {LOADING_MESSAGES[currentMessageIndex]}
                  </p>
                  <div className="w-full bg-muted/30 rounded-full h-2 mt-4">
                    <div className="bg-primary h-2 rounded-full animate-pulse" style={{width: `${((currentMessageIndex + 1) / LOADING_MESSAGES.length) * 100}%`}}></div>
                  </div>
                </div>
              </div>
            </Card>
          </section>
        )}

        {/* Results Section */}
        {processedResume && !isProcessing && (
          <section className="max-w-2xl mx-auto mt-8">
            <Card className="border border-border/30 shadow-lg backdrop-blur-sm bg-card/50 p-6 sm:p-8">
              <div className="space-y-6">
                {processedResume.success ? (
                  <div className="text-center space-y-4">
                    <div className="flex justify-center">
                      <CheckCircle className="h-16 w-16 text-green-500" />
                    </div>
                    <div>
                      <h3 className="text-xl sm:text-2xl font-bold text-green-500">Success!</h3>
                      <p className="text-sm sm:text-base text-muted-foreground mt-2">
                        Your ATS-optimized resume has been generated and downloaded!
                      </p>
                    </div>
                    <Button
                      onClick={resetForm}
                      variant="outline"
                      className="hover:scale-[1.02] transition-all duration-300"
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
                      <h3 className="text-xl sm:text-2xl font-bold text-destructive">Processing Failed</h3>
                      <p className="text-sm sm:text-base text-muted-foreground mt-2 px-4">
                        {processedResume.error || "An unexpected error occurred"}
                      </p>
                    </div>
                    <div className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4">
                      <Button
                        onClick={retrySubmit}
                        className="gradient-purple-blue hover:scale-[1.02] transition-all duration-300 text-white border-0"
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Try Again
                      </Button>
                      <Button
                        onClick={resetForm}
                        variant="outline"
                        className="hover:scale-[1.02] transition-all duration-300"
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
      <footer className="border-t border-border/20 mt-16 sm:mt-24">
        <div className="container mx-auto px-4 py-6 sm:py-8">
          <div className="flex flex-col items-center text-center space-y-4">
            <p className="text-xs sm:text-sm text-muted-foreground">
              © 2024 Resume Optimizer. All rights reserved.
            </p>
            <div className="flex space-x-4 sm:space-x-6">
              <a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-primary transition-colors">
                Privacy
              </a>
              <a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-primary transition-colors">
                Terms
              </a>
              <a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-primary transition-colors">
                Support
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
