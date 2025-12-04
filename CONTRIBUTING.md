# Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Ways to Contribute

### Bug Reports
- Search existing issues before creating a new one
- Use the issue templates when available
- Include detailed steps to reproduce the problem
- Provide system information (OS, Docker version, etc.)

### Feature Requests
- Check if the feature has already been requested
- Clearly describe the use case and expected behavior
- Consider if the feature fits the project's scope and goals

### Code Contributions
- Fork the repository and create a feature branch
- Follow the existing code style and conventions
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting

## Development Setup

See the main [README.md](README.md) for detailed setup instructions, including:
- Azure infrastructure deployment
- Local development with Docker or manual setup
- Running tests and evaluations

## Pull Request Guidelines

1. **Branch naming**: Use descriptive names like `feature/add-evaluation-metrics` or `fix/docker-build-error`

2. **Commit messages**: Write clear, descriptive commit messages
   ```
   feat: add support for custom evaluation criteria
   fix: resolve Docker build issues with Node.js dependencies
   docs: update API documentation for agent endpoints
   ```

3. **Testing**: Ensure your changes work with both Docker and local development setups

4. **Documentation**: Update relevant documentation in README files

5. **Small PRs**: Keep pull requests focused on a single feature or fix

## Code Style

### Python
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings for functions and classes

### TypeScript/React
- Use existing ESLint and Prettier configurations
- Follow React best practices and hooks patterns
- Maintain consistent component structure

### General
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused

## Areas for Contribution

We welcome contributions in these areas:
- **Agent integrations**: Support for additional agent frameworks
- **Evaluation metrics**: New ways to measure agent performance  
- **UI improvements**: Better visualization of test results
- **Documentation**: Tutorials, examples, and guides
- **Performance**: Optimizations for large-scale evaluations
- **Testing**: Improved test coverage and test utilities

## Questions?

If you have questions about contributing:
- Check existing issues and discussions
- Review the documentation in the `src/` directories
- Contact the maintainers through GitHub issues

Thank you for your interest in improving Evals for Agent Interop!