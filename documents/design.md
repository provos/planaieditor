# Design Document: Node-Based AI Agent Builder with PlanAI Integration

## 1. Executive Summary

This document outlines the design for a graphical user interface (GUI) application that simplifies the creation of AI agents using PlanAI. The tool will provide a node-based interface for configuring AI workflows without requiring extensive Python boilerplate code. The application will use Svelte 5 with SvelteKit for the frontend and integrate svelte-flow for the node-based graph interface, with a Python backend for executing PlanAI workflows.

## 2. Project Objectives

- Create an intuitive node-based interface for PlanAI
- Reduce the learning curve for building AI agent workflows
- Enable import of existing PlanAI Python code
- Provide specialized editors for different node types
- Support data-type specific routing between nodes
- Allow execution and validation of the created workflows

## 3. System Architecture

### 3.1 Frontend (Svelte 5 with SvelteKit)

- **UI Components**:
  - Node Graph Editor (svelte-flow)
  - Node Configuration Panels
  - Code Editor (CodeMirror)
  - Task/Model Definition Interface
  - Workflow Control Panel (Start, Stop, Debug)
  - Import/Export Tools

- **State Management**:
  - Graph structure state
  - Node configuration state
  - Validation state
  - Execution state

### 3.2 Backend (Python)

- **Core Services**:
  - PlanAI Integration Layer
  - Code Validation Service
  - AST Parser for PlanAI Code Import
  - Workflow Execution Engine
  - Type Checking System

### 3.3 Communication Layer

- RESTful API for configuration and management
- WebSocket for real-time updates during workflow execution

## 4. Detailed Component Design

### 4.1 Node Graph Editor

- **Node Types**:
  - Task Definition Nodes
  - TaskWorker Nodes
  - LLMWorker Nodes
  - CachedLLMWorker Nodes
  - Custom Worker Nodes

- **Connection Management**:
  - Type-safe connections with validation
  - Visual indicators for compatible/incompatible connections
  - Data-type labeling on connection points

- **UI Features**:
  - Zoom and pan controls
  - Node grouping
  - Mini-map for navigation
  - Search functionality

### 4.2 Node Configuration Panels

#### 4.2.1 Task Definition Panel
- Pydantic model definition interface
- Field type specification
- Default value configuration
- Inheritance configuration

#### 4.2.2 TaskWorker Configuration Panel
- Input/output type selection
- Processing logic editor (CodeMirror)
- Worker settings configuration

#### 4.2.3 LLMWorker Configuration Panel
- Prompt template editor with variables
- System prompt editor
- LLM model selection and parameters
- Output parsing configuration

### 4.3 Code Editor Integration

- **CodeMirror Features**:
  - Syntax highlighting for Python
  - Auto-completion
  - Error highlighting
  - Code folding

- **Integration Points**:
  - Custom Python code for TaskWorkers
  - Type definition code
  - Pre/post processing hooks

### 4.4 Import/Export System

- **Python Code Parser**:
  - AST-based parsing of PlanAI Python code
  - Conversion to node graph representation
  - Mapping of Python functions to node configurations

- **Export Functionality**:
  - Generate executable PlanAI Python code
  - Save/load graph configurations
  - Version control integration

### 4.5 Type System

- **Type Definition**:
  - Interface for defining custom types
  - Visualization of type hierarchies
  - Type compatibility checking

- **Connection Validation**:
  - Real-time validation of node connections
  - Type mismatch warnings
  - Automatic type conversion suggestions

## 5. Backend Services

### 5.1 PlanAI Integration Layer

- Direct mapping of UI elements to PlanAI constructs
- Configuration translation between UI state and PlanAI parameters
- Execution bridging

### 5.2 Code Validation Service

- Real-time Python code validation
- Integration with PlanAI constraints
- Security scanning for potentially harmful code

### 5.3 AST Parser for Code Import

- Parse existing PlanAI Python code
- Extract Task definitions, TaskWorkers, and workflow structures
- Convert to UI graph representation

### 5.4 Workflow Execution Engine

- Execute the configured graph using PlanAI
- Provide execution status updates
- Capture and display execution results
- Support for debugging and step-by-step execution

## 6. User Workflows

### 6.1 Creating a New Agent

1. User creates a new project
2. User adds Task nodes to define data models
3. User adds Worker nodes to process the tasks
4. User connects nodes according to data flow
5. User configures each node (prompts, code, settings)
6. User validates the workflow
7. User executes the workflow

### 6.2 Importing Existing PlanAI Code

1. User selects import option
2. User provides Python file or code snippet
3. System parses the code into an AST
4. System generates equivalent node graph
5. User reviews and adjusts the imported graph
6. User can continue development with the GUI

### 6.3 Exporting to Python

1. User finalizes node graph
2. User selects export option
3. System generates executable PlanAI Python code
4. User can save or copy the generated code

## 7. Implementation Plan

### 7.1 Phase 1: Core Infrastructure

- Set up SvelteKit project
- Integrate svelte-flow
- Create basic node types
- Implement backend API structure
- Establish WebSocket communication

### 7.2 Phase 2: Node Editor Functionality

- Implement node configuration panels
- Add CodeMirror integration
- Create type system
- Build connection validation

### 7.3 Phase 3: PlanAI Integration

- Develop PlanAI execution bridge
- Implement code validation service
- Add workflow execution functionality
- Create monitoring and debugging tools

### 7.4 Phase 4: Import/Export System

- Build AST parser for Python code
- Implement graph-to-code export
- Add save/load functionality
- Create project management features

### 7.5 Phase 5: Polish and Testing

- User testing and feedback
- Performance optimization
- Documentation
- Tutorials and examples

## 8. Technical Considerations

### 8.1 Data Model

```typescript
// Core node interface
interface Node {
  id: string;
  type: NodeType;
  position: { x: number, y: number };
  data: NodeData;
}

// Task definition node
interface TaskNode extends Node {
  type: 'task';
  data: {
    name: string;
    fields: Array<{
      name: string;
      type: string;
      required: boolean;
      default?: any;
    }>;
    baseClass?: string;
  };
}

// Worker node
interface WorkerNode extends Node {
  type: 'worker' | 'llmWorker' | 'cachedLLMWorker';
  data: {
    name: string;
    inputs: Array<{
      name: string;
      type: string;
    }>;
    outputs: Array<{
      name: string;
      type: string;
    }>;
    code?: string;
    prompt?: string;
    system_prompt?: string;
    llmConfig?: any;
  };
}

// Connection type
interface Connection {
  id: string;
  source: string;
  target: string;
  sourceHandle: string;
  targetHandle: string;
}
```

### 8.2 API Endpoints

```
GET /api/models - List available LLM models
POST /api/validate - Validate Python code
POST /api/parse - Parse Python code to node graph
POST /api/execute - Execute workflow
GET /api/status/:id - Get execution status
POST /api/export - Export to Python code
```

### 8.3 WebSocket Events

```
execution:start - Workflow execution started
execution:progress - Execution progress update
execution:node:start - Node execution started
execution:node:complete - Node execution completed
execution:node:error - Node execution error
execution:complete - Workflow execution complete
```

## 9. UI Mockups

[Note: In a complete design document, this section would contain wireframes or mockups of the main UI components.]

## 10. Security Considerations

- Code execution sandboxing
- Input validation for all API endpoints
- Rate limiting for execution requests
- Authentication for accessing workflows
- Secure storage of API keys and credentials

## 11. Future Extensions

- Marketplace for sharing components and workflows
- Version control integration
- Collaborative editing
- Custom node development SDK
- Integration with other AI frameworks
- Performance monitoring and optimization tools
- Automated testing of workflows

## 12. Conclusion

This node-based AI agent builder will significantly reduce the barrier to entry for working with PlanAI. By providing an intuitive visual interface with strong type checking and code validation, it will enable users to create complex AI workflows without extensive Python knowledge. The ability to import existing code and export to executable Python ensures compatibility with the existing PlanAI ecosystem.