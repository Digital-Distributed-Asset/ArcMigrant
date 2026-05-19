// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ICircleGateway
 * Circle Gateway crosschain USDC interface for Arc.
 * Full docs: https://developers.circle.com/gateway
 */
interface ICircleGateway {
    function transferUSDC(
        uint32 destinationDomain,
        address recipient,
        uint256 amount
    ) external;

    function getDomainForChain(uint256 chainId) external view returns (uint32 domain);
}

